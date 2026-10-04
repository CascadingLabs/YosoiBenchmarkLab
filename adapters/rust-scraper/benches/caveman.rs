use std::{env, fs, hint::black_box};

use criterion::{Criterion, criterion_group, criterion_main};
use scraper::{Html, Selector};

fn normalize(value: &str) -> String {
    value.split_whitespace().collect::<Vec<_>>().join(" ")
}

fn locate(document: &Html, selector: &Selector) -> Vec<String> {
    document
        .select(selector)
        .map(|element| normalize(&element.text().collect::<String>()))
        .collect()
}

fn benchmark(criterion: &mut Criterion) {
    let fixture = env::var("YOSOI_BENCHMARK_FIXTURE").unwrap_or_else(|_| {
        panic!("YOSOI_BENCHMARK_FIXTURE must name the generated caveman fixture")
    });
    let data = fs::read(fixture).unwrap_or_else(|error| panic!("failed to read fixture: {error}"));
    let text =
        std::str::from_utf8(&data).unwrap_or_else(|error| panic!("fixture is not UTF-8: {error}"));
    let selector = Selector::parse("article.product-card[data-sku='sku-000073'] span.price")
        .unwrap_or_else(|error| panic!("selector is invalid: {error:?}"));
    let parsed = Html::parse_document(text);
    assert_eq!(locate(&parsed, &selector), ["USD 19.73"]);

    criterion.bench_function("rustScraper/parse", |bencher| {
        bencher.iter(|| black_box(Html::parse_document(black_box(text))));
    });
    criterion.bench_function("rustScraper/locate", |bencher| {
        bencher.iter(|| black_box(locate(black_box(&parsed), black_box(&selector))));
    });
    criterion.bench_function("rustScraper/endToEnd", |bencher| {
        bencher.iter(|| {
            let document = Html::parse_document(black_box(text));
            black_box(locate(&document, black_box(&selector)))
        });
    });
}

criterion_group!(benches, benchmark);
criterion_main!(benches);
