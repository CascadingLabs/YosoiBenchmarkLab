use std::{env, sync::Arc, time::Instant};

use anyhow::{Context, Result, bail};
use futures_util::{StreamExt, stream};
use serde::Serialize;
use yosoi::prelude as ys;

#[derive(Debug)]
struct Arguments {
    base: String,
    count: usize,
    concurrency: usize,
    delay_ms: usize,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct Output {
    arm_id: &'static str,
    language: &'static str,
    count: usize,
    concurrency: usize,
    delay_ms: usize,
    wall_ns: u64,
    throughput_requests_per_second: f64,
    terminal_status: &'static str,
    values: Vec<String>,
}

fn arguments() -> Result<Arguments> {
    let mut base = None;
    let mut count = None;
    let mut concurrency = None;
    let mut delay_ms = None;
    let mut values = env::args().skip(1);
    while let Some(name) = values.next() {
        let value = values
            .next()
            .with_context(|| format!("missing value for {name}"))?;
        match name.as_str() {
            "--base" => base = Some(value),
            "--count" => count = Some(value.parse()?),
            "--concurrency" => concurrency = Some(value.parse()?),
            "--delay-ms" => delay_ms = Some(value.parse()?),
            _ => bail!("unsupported argument: {name}"),
        }
    }
    let result = Arguments {
        base: base.context("--base is required")?,
        count: count.context("--count is required")?,
        concurrency: concurrency.context("--concurrency is required")?,
        delay_ms: delay_ms.context("--delay-ms is required")?,
    };
    if result.count == 0 || result.concurrency == 0 {
        bail!("count and concurrency must be positive");
    }
    Ok(result)
}

fn document_value(document: &ys::Document, plan: &ys::Plan) -> Result<String> {
    let outcome = document.locate(plan);
    let ys::LocateOutcome::Matched { result } = outcome else {
        bail!("response document did not match the value locator: {outcome:?}");
    };
    let finding = result
        .findings()
        .first()
        .context("value finding is missing")?;
    match finding.value() {
        ys::ProjectedValue::Text(value) => Ok(value.clone()),
        value => bail!("unexpected projected value: {value:?}"),
    }
}

async fn fetch_one(
    index: usize,
    target: String,
    plan: Arc<ys::Plan>,
    policy: Arc<ys::Policy>,
) -> Result<(usize, String)> {
    let response = ys::request::new(target).bind(&policy).send().await?;
    let attempt = response
        .attempts()
        .first()
        .context("response has no attempt")?;
    let document = attempt
        .result()
        .and_then(|result| result.documents().first())
        .and_then(|outcome| outcome.outcome().document())
        .context("response document is missing")?;
    Ok((index, document_value(document, &plan)?))
}

async fn run(arguments: Arguments) -> Result<()> {
    let plan = Arc::new(ys::Plan::new([ys::output(
        "value",
        ys::css("span.value")?.text(),
    )?])?);
    let mut policy = ys::Policy::default();
    policy.page.acquisitions = vec![
        ys::policy::Acquisition::Browser(ys::BrowserMode::Headless)
            .documents([ys::policy::DocumentRequest::RenderedDom]),
    ];
    let policy = Arc::new(policy);
    let targets = (0..arguments.count)
        .map(|index| {
            (
                index,
                format!(
                    "{}/dynamic?id={index}&delayMs={}",
                    arguments.base, arguments.delay_ms
                ),
            )
        })
        .collect::<Vec<_>>();
    let started = Instant::now();
    let results = stream::iter(targets)
        .map(|(index, target)| fetch_one(index, target, plan.clone(), policy.clone()))
        .buffer_unordered(arguments.concurrency)
        .collect::<Vec<_>>()
        .await;
    let wall_ns = u64::try_from(started.elapsed().as_nanos())?;
    let mut values = results.into_iter().collect::<Result<Vec<_>>>()?;
    values.sort_by_key(|(index, _)| *index);
    let values = values
        .into_iter()
        .map(|(_, value)| value)
        .collect::<Vec<_>>();
    let correct = values
        .iter()
        .enumerate()
        .all(|(index, value)| value == &format!("value-{index}"));
    let output = Output {
        arm_id: "yosoiBrowserRequest",
        language: "rust",
        count: arguments.count,
        concurrency: arguments.concurrency,
        delay_ms: arguments.delay_ms,
        wall_ns,
        throughput_requests_per_second: arguments.count as f64 / (wall_ns as f64 / 1e9),
        terminal_status: if correct { "ok" } else { "wrongOutput" },
        values,
    };
    println!("{}", serde_json::to_string(&output)?);
    if !correct {
        bail!("output oracle failed");
    }
    Ok(())
}

fn main() -> Result<()> {
    let arguments = arguments()?;
    let runtime = tokio::runtime::Builder::new_multi_thread()
        .worker_threads(arguments.concurrency)
        .enable_all()
        .build()?;
    runtime.block_on(run(arguments))
}
