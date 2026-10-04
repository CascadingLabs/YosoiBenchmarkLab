use std::{env, fs, hint::black_box};

use criterion::{Criterion, criterion_group, criterion_main};
use yosoi::prelude as ys;

fn values(outcome: ys::LocateOutcome) -> Vec<String> {
    match outcome {
        ys::LocateOutcome::Matched { result } => result
            .findings()
            .iter()
            .filter_map(|finding| match finding.value() {
                ys::ProjectedValue::Text(value) => Some(value.clone()),
                _ => None,
            })
            .collect(),
        _ => Vec::new(),
    }
}

fn benchmark(criterion: &mut Criterion) {
    let fixture = env::var("YOSOI_BENCHMARK_FIXTURE").unwrap_or_else(|_| {
        panic!("YOSOI_BENCHMARK_FIXTURE must name the generated caveman fixture")
    });
    let data = fs::read(fixture).unwrap_or_else(|error| panic!("failed to read fixture: {error}"));
    let document = ys::Document::html("cavemanCatalog.html", data)
        .unwrap_or_else(|error| panic!("fixture document is invalid: {error}"));
    let plan = ys::Plan::new([ys::output(
        "price",
        ys::css("article.product-card[data-sku='sku-000073'] span.price")
            .unwrap_or_else(|error| panic!("selector is invalid: {error}"))
            .text(),
    )
    .unwrap_or_else(|error| panic!("output is invalid: {error}"))])
    .unwrap_or_else(|error| panic!("plan is invalid: {error}"));
    let parsed = document
        .parse()
        .unwrap_or_else(|error| panic!("fixture parse failed: {error}"));
    assert_eq!(values(document.locate(&plan)), ["USD 19.73"]);

    criterion.bench_function("yosoiRust/parse", |bencher| {
        bencher.iter(|| {
            black_box(
                document
                    .parse()
                    .unwrap_or_else(|error| panic!("parse failed: {error}")),
            )
        });
    });
    criterion.bench_function("yosoiRust/locate", |bencher| {
        bencher.iter(|| black_box(values(parsed.locate(black_box(&plan)))));
    });
    criterion.bench_function("yosoiRust/endToEnd", |bencher| {
        bencher.iter(|| black_box(values(document.locate(black_box(&plan)))));
    });
}

criterion_group!(benches, benchmark);
criterion_main!(benches);
