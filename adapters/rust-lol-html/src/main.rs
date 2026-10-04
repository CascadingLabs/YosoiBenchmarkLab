use std::{
    borrow::Cow, cell::RefCell, env, ffi::OsStr, hint::black_box, io, path::PathBuf, rc::Rc,
    time::Instant,
};

use anyhow::{Context, Result, bail};
use lol_html::{
    ElementContentHandlers, ElementHandler, HtmlRewriter, Selector, Settings, TextHandler,
    html_content::Element,
};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

mod input;

use input::read_bounded;

const TARGET_SELECTOR: &str = "article.product-card[data-selected='true'] span.price";
const CAVEMAN_SELECTOR: &str = "article.product-card[data-sku='sku-000073'] span.price";
const MAX_FIXTURE_BYTES: usize = 32 * 1024 * 1024;
const MAX_MANIFEST_BYTES: usize = 1024 * 1024;
const MAX_CHUNK_BYTES: usize = 1024 * 1024;
const MAX_SAMPLES: usize = 100;
const MAX_OPERATIONS: usize = 100;

#[derive(Debug)]
struct Arguments {
    fixture: PathBuf,
    manifest: PathBuf,
    task: String,
    phase: String,
    samples: usize,
    operations: usize,
    chunk_size: usize,
    check_chunk_sizes: Vec<usize>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct FixtureManifest {
    fixtures: Vec<FixtureEntry>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct FixtureEntry {
    id: String,
    path: String,
    bytes: usize,
    sha256: String,
    expected_values: Vec<String>,
    expected_values_sha256: String,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct ChunkParity {
    chunk_size: usize,
    match_count: usize,
    output_sha256: String,
    exact_output: bool,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct Output {
    schema_version: &'static str,
    arm_id: &'static str,
    language: &'static str,
    runtime: &'static str,
    product_version: &'static str,
    backend: &'static str,
    effective_query: &'static str,
    streaming_mode: &'static str,
    task: String,
    phase: String,
    terminal_status: String,
    failure_reason: Option<String>,
    match_count: usize,
    values: Vec<String>,
    output_sha256: String,
    expected_values_sha256: String,
    input_sha256: String,
    samples_ns: Vec<u64>,
    operations_per_sample: usize,
    input_bytes: usize,
    chunk_size: usize,
    chunk_parity: Vec<ChunkParity>,
}

#[derive(Default)]
struct Capture {
    open_text: Vec<String>,
    values: Vec<String>,
}

fn next_value(arguments: &mut impl Iterator<Item = String>, name: &str) -> Result<String> {
    arguments
        .next()
        .with_context(|| format!("missing value for {name}"))
}

fn parse_chunk_sizes(value: &str) -> Result<Vec<usize>> {
    let sizes = value
        .split(',')
        .map(|item| {
            item.parse::<usize>()
                .with_context(|| format!("invalid chunk size: {item}"))
        })
        .collect::<Result<Vec<_>>>()?;
    if sizes.is_empty()
        || sizes
            .iter()
            .any(|size| *size == 0 || *size > MAX_CHUNK_BYTES)
    {
        bail!("chunk sizes must be between 1 and {MAX_CHUNK_BYTES} bytes");
    }
    Ok(sizes)
}

fn parse_arguments() -> Result<Arguments> {
    let mut fixture = None;
    let mut manifest = None;
    let mut task = None;
    let mut phase = None;
    let mut samples = None;
    let mut operations = None;
    let mut chunk_size = None;
    let mut check_chunk_sizes = Vec::new();
    let mut arguments = env::args().skip(1);

    while let Some(argument) = arguments.next() {
        match argument.as_str() {
            "--fixture" => fixture = Some(PathBuf::from(next_value(&mut arguments, "--fixture")?)),
            "--manifest" => {
                manifest = Some(PathBuf::from(next_value(&mut arguments, "--manifest")?))
            }
            "--task" => task = Some(next_value(&mut arguments, "--task")?),
            "--phase" => phase = Some(next_value(&mut arguments, "--phase")?),
            "--samples" => {
                samples = Some(
                    next_value(&mut arguments, "--samples")?
                        .parse()
                        .context("samples must be an integer")?,
                )
            }
            "--operations" => {
                operations = Some(
                    next_value(&mut arguments, "--operations")?
                        .parse()
                        .context("operations must be an integer")?,
                )
            }
            "--chunk-size" => {
                chunk_size = Some(
                    next_value(&mut arguments, "--chunk-size")?
                        .parse()
                        .context("chunk size must be an integer")?,
                )
            }
            "--check-chunk-sizes" => {
                check_chunk_sizes =
                    parse_chunk_sizes(&next_value(&mut arguments, "--check-chunk-sizes")?)?
            }
            _ => bail!("unsupported argument: {argument}"),
        }
    }

    let result = Arguments {
        fixture: fixture.context("--fixture is required")?,
        manifest: manifest.context("--manifest is required")?,
        task: task.context("--task is required")?,
        phase: phase.context("--phase is required")?,
        samples: samples.context("--samples is required")?,
        operations: operations.context("--operations is required")?,
        chunk_size: chunk_size.context("--chunk-size is required")?,
        check_chunk_sizes,
    };
    if !matches!(result.task.as_str(), "caveman" | "hard") || result.phase != "endToEnd" {
        bail!("only caveman/hard endToEnd byte-to-value operations are supported");
    }
    if result.operations == 0 || result.operations > MAX_OPERATIONS {
        bail!("operations must be between 1 and {MAX_OPERATIONS}");
    }
    if result.samples > MAX_SAMPLES {
        bail!("samples must not exceed {MAX_SAMPLES}");
    }
    if result.chunk_size == 0 || result.chunk_size > MAX_CHUNK_BYTES {
        bail!("chunk size must be between 1 and {MAX_CHUNK_BYTES} bytes");
    }
    Ok(result)
}

fn digest_hex(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

fn digest_values(values: &[String]) -> Result<String> {
    Ok(digest_hex(&serde_json::to_vec(values)?))
}

fn normalize(value: &str) -> String {
    value.split_whitespace().collect::<Vec<_>>().join(" ")
}

fn handler_error(message: &'static str) -> Box<dyn std::error::Error + Send + Sync> {
    io::Error::other(message).into()
}

fn stream_values(data: &[u8], chunk_size: usize, selector: &Selector) -> Result<Vec<String>> {
    let capture = Rc::new(RefCell::new(Capture::default()));
    let element_capture = Rc::clone(&capture);
    let element_handler: ElementHandler<'_> = Box::new(move |element: &mut Element<'_, '_>| {
        element_capture
            .try_borrow_mut()
            .map_err(|_| handler_error("reentrant element capture"))?
            .open_text
            .push(String::new());

        let end_capture = Rc::clone(&element_capture);
        element.on_end_tag(Box::new(move |_| {
            let mut state = end_capture
                .try_borrow_mut()
                .map_err(|_| handler_error("reentrant end-tag capture"))?;
            let Some(value) = state.open_text.pop() else {
                return Err(handler_error(
                    "selected element ended without capture state",
                ));
            };
            state.values.push(normalize(&value));
            Ok(())
        }))?;
        Ok(())
    });

    let text_capture = Rc::clone(&capture);
    let text_handler: TextHandler<'_> = Box::new(move |chunk| {
        let mut state = text_capture
            .try_borrow_mut()
            .map_err(|_| handler_error("reentrant text capture"))?;
        let Some(current) = state.open_text.last_mut() else {
            return Err(handler_error(
                "selected text arrived without an open element",
            ));
        };
        current.push_str(chunk.as_str());
        Ok(())
    });

    let settings = Settings::new().append_element_content_handler((
        Cow::Borrowed(selector),
        ElementContentHandlers {
            element: Some(element_handler),
            comments: None,
            text: Some(text_handler),
        },
    ));
    let mut rewriter = HtmlRewriter::new(settings, |_output: &[u8]| {});
    for chunk in data.chunks(chunk_size) {
        rewriter
            .write(chunk)
            .context("lol-html failed to write a chunk")?;
    }
    rewriter
        .end()
        .context("lol-html failed to finalize the stream")?;

    let state = Rc::try_unwrap(capture)
        .map_err(|_| anyhow::anyhow!("lol-html retained a capture handler after finalization"))?
        .into_inner();
    if !state.open_text.is_empty() {
        bail!("selected elements were not closed by the stream");
    }
    Ok(state.values)
}

fn main() -> Result<()> {
    let arguments = parse_arguments()?;
    let manifest_bytes = read_bounded(&arguments.manifest, MAX_MANIFEST_BYTES)?;
    let manifest: FixtureManifest = serde_json::from_slice(&manifest_bytes)
        .context("fixture manifest is not valid benchmark JSON")?;
    let fixture_entry = manifest
        .fixtures
        .iter()
        .find(|fixture| fixture.id == if arguments.task == "caveman" { "cavemanCatalog" } else { "hardCatalog" })
        .context("manifest has no requested fixture")?;
    if arguments.fixture.file_name() != Some(OsStr::new(&fixture_entry.path)) {
        bail!("fixture path does not match the manifest");
    }
    let data = read_bounded(&arguments.fixture, MAX_FIXTURE_BYTES)?;
    let input_sha256 = digest_hex(&data);
    if data.len() != fixture_entry.bytes || input_sha256 != fixture_entry.sha256 {
        bail!("fixture bytes or SHA-256 differ from the manifest");
    }
    let expected_values_sha256 = digest_values(&fixture_entry.expected_values)?;
    if expected_values_sha256 != fixture_entry.expected_values_sha256 {
        bail!("oracle values or SHA-256 differ from the manifest");
    }

    let effective_query = if arguments.task == "caveman" { CAVEMAN_SELECTOR } else { TARGET_SELECTOR };
    let selector: Selector = effective_query
        .parse()
        .map_err(|error| anyhow::anyhow!("invalid frozen selector: {error:?}"))?;
    let mut chunk_parity = Vec::with_capacity(arguments.check_chunk_sizes.len());
    let mut primary_values = None;
    let mut failure_reason = None;
    for chunk_size in &arguments.check_chunk_sizes {
        let observed = stream_values(&data, *chunk_size, &selector)
            .with_context(|| format!("preflight failed at chunk size {chunk_size}"))?;
        let exact_output = observed == fixture_entry.expected_values;
        if !exact_output {
            failure_reason = Some(format!("exact output mismatch at chunk size {chunk_size}"));
        }
        chunk_parity.push(ChunkParity {
            chunk_size: *chunk_size,
            match_count: observed.len(),
            output_sha256: digest_values(&observed)?,
            exact_output,
        });
        if *chunk_size == arguments.chunk_size {
            primary_values = Some(observed);
        }
    }
    let mut values = match primary_values {
        Some(values) => values,
        None => stream_values(&data, arguments.chunk_size, &selector)
            .context("primary chunk-size preflight failed")?,
    };
    if values != fixture_entry.expected_values {
        failure_reason = Some(format!(
            "exact output mismatch at chunk size {}",
            arguments.chunk_size
        ));
    }

    let mut samples_ns = Vec::with_capacity(arguments.samples);
    if failure_reason.is_none() {
        'samples: for _ in 0..arguments.samples {
            let started = Instant::now();
            for _ in 0..arguments.operations {
                values = black_box(stream_values(
                    &data,
                    arguments.chunk_size,
                    &selector,
                )?);
            }
            let divisor = u128::try_from(arguments.operations)
                .context("operation count does not fit u128")?;
            let elapsed = started.elapsed().as_nanos() / divisor;
            if values != fixture_entry.expected_values {
                failure_reason = Some("exact output mismatch in measured operation".to_owned());
                break 'samples;
            }
            samples_ns.push(u64::try_from(elapsed).context("sample does not fit u64 nanoseconds")?);
        }
    }

    let output = Output {
        schema_version: "yosoi.benchmark.adapter.v1",
        arm_id: "lolHtml",
        language: "rust",
        runtime: option_env!("YOSOI_BENCHMARK_RUST_VERSION").unwrap_or("unrecorded Rust toolchain"),
        product_version: "3.0.1",
        backend: "lol_html::HtmlRewriter",
        effective_query,
        streaming_mode: "incremental",
        task: arguments.task,
        phase: arguments.phase,
        terminal_status: if failure_reason.is_some() {
            "wrongOutput"
        } else {
            "ok"
        }
        .to_owned(),
        failure_reason,
        match_count: values.len(),
        output_sha256: digest_values(&values)?,
        values,
        expected_values_sha256,
        input_sha256,
        samples_ns,
        operations_per_sample: arguments.operations,
        input_bytes: data.len(),
        chunk_size: arguments.chunk_size,
        chunk_parity,
    };
    println!("{}", serde_json::to_string(&output)?);
    Ok(())
}

#[cfg(test)]
mod tests;
