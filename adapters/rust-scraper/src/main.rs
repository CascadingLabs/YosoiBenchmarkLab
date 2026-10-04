use std::{env, fs, hint::black_box, time::Instant};

use anyhow::{Context, Result, bail};
use scraper::{Html, Selector};
use serde::Serialize;
use sha2::{Digest, Sha256};

#[derive(Debug)]
struct Arguments {
    fixture: String,
    task: String,
    phase: String,
    samples: usize,
    operations: usize,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct Output {
    schema_version: &'static str,
    arm_id: &'static str,
    language: &'static str,
    runtime: String,
    product_version: &'static str,
    task: String,
    phase: String,
    terminal_status: &'static str,
    match_count: usize,
    values: Vec<String>,
    output_sha256: String,
    samples_ns: Vec<u64>,
    operations_per_sample: usize,
    input_bytes: usize,
}

fn parse_arguments() -> Result<Arguments> {
    let mut fixture = None;
    let mut task = None;
    let mut phase = None;
    let mut samples = None;
    let mut operations = None;
    let mut arguments = env::args().skip(1);
    while let Some(argument) = arguments.next() {
        let value = arguments
            .next()
            .with_context(|| format!("missing value for {argument}"))?;
        match argument.as_str() {
            "--fixture" => fixture = Some(value),
            "--task" => task = Some(value),
            "--phase" => phase = Some(value),
            "--samples" => samples = Some(value.parse().context("samples must be an integer")?),
            "--operations" => {
                operations = Some(value.parse().context("operations must be an integer")?)
            }
            _ => bail!("unsupported argument: {argument}"),
        }
    }
    let result = Arguments {
        fixture: fixture.context("--fixture is required")?,
        task: task.context("--task is required")?,
        phase: phase.context("--phase is required")?,
        samples: samples.context("--samples is required")?,
        operations: operations.context("--operations is required")?,
    };
    if result.operations == 0 {
        bail!("operations must be positive");
    }
    Ok(result)
}

fn selector_for(task: &str) -> Result<Selector> {
    let expression = match task {
        "caveman" => "article.product-card[data-sku='sku-000073'] span.price",
        "hard" => "article.product-card[data-selected='true'] span.price",
        _ => bail!("unsupported task: {task}"),
    };
    Selector::parse(expression).map_err(|error| anyhow::anyhow!("invalid selector: {error:?}"))
}

fn normalize(value: &str) -> String {
    value.split_whitespace().collect::<Vec<_>>().join(" ")
}

fn locate(document: &Html, selector: &Selector) -> Vec<String> {
    document
        .select(selector)
        .map(|element| normalize(&element.text().collect::<String>()))
        .collect()
}

fn digest_values(values: &[String]) -> Result<String> {
    let bytes = serde_json::to_vec(values)?;
    Ok(format!("{:x}", Sha256::digest(bytes)))
}

fn elapsed_per_operation(started: Instant, operations: usize) -> Result<u64> {
    let divisor = u128::try_from(operations).context("operation count does not fit u128")?;
    let elapsed = started.elapsed().as_nanos() / divisor;
    u64::try_from(elapsed).context("elapsed nanoseconds do not fit u64")
}

fn main() -> Result<()> {
    let arguments = parse_arguments()?;
    let data = fs::read(&arguments.fixture)
        .with_context(|| format!("failed to read {}", arguments.fixture))?;
    let text = std::str::from_utf8(&data).context("fixture is not UTF-8")?;
    let selector = selector_for(&arguments.task)?;
    let parsed = Html::parse_document(text);
    let expected_values = locate(&parsed, &selector);
    let mut samples_ns = Vec::with_capacity(arguments.samples);

    for _ in 0..arguments.samples {
        let started = Instant::now();
        let mut last_values = Vec::new();
        match arguments.phase.as_str() {
            "parse" => {
                for _ in 0..arguments.operations {
                    black_box(Html::parse_document(black_box(text)));
                }
                last_values.clone_from(&expected_values);
            }
            "locate" => {
                for _ in 0..arguments.operations {
                    last_values = black_box(locate(black_box(&parsed), black_box(&selector)));
                }
            }
            "endToEnd" => {
                for _ in 0..arguments.operations {
                    let document = Html::parse_document(black_box(text));
                    last_values = black_box(locate(&document, black_box(&selector)));
                }
            }
            phase => bail!("unsupported phase: {phase}"),
        }
        let per_operation = elapsed_per_operation(started, arguments.operations)?;
        if arguments.phase != "parse" && last_values != expected_values {
            bail!("measured output changed from correctness preflight");
        }
        samples_ns.push(per_operation);
    }

    let output = Output {
        schema_version: "yosoi.benchmark.adapter.v1",
        arm_id: "rustScraper",
        language: "rust",
        runtime: "rust-1.98.0".to_owned(),
        product_version: "0.27.0",
        task: arguments.task,
        phase: arguments.phase,
        terminal_status: "ok",
        match_count: expected_values.len(),
        output_sha256: digest_values(&expected_values)?,
        values: expected_values,
        samples_ns,
        operations_per_sample: arguments.operations,
        input_bytes: data.len(),
    };
    println!("{}", serde_json::to_string(&output)?);
    Ok(())
}
