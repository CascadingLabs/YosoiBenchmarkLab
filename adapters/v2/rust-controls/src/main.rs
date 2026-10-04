use std::{collections::BTreeMap, env, fs, hint::black_box, time::Instant};

use anyhow::{Context, Result, bail};
use regex::Regex;
use scraper::{Html, Selector};
use serde::Serialize;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};

#[derive(Debug)]
struct Arguments {
    arm: String,
    cell: String,
    document_class: String,
    query_family: String,
    expression: String,
    projection: String,
    phase: String,
    fixture: String,
    samples: usize,
    operations: usize,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct Output {
    schema_version: &'static str,
    arm_id: String,
    cell_id: String,
    document_class: String,
    query_family: String,
    projection: String,
    phase: String,
    terminal_status: &'static str,
    match_count: usize,
    values: Vec<Value>,
    output_sha256: String,
    samples_ns: Vec<u64>,
    operations_per_sample: usize,
    input_bytes: usize,
}

fn arguments() -> Result<Arguments> {
    let mut arm = None;
    let mut cell = None;
    let mut document_class = None;
    let mut query_family = None;
    let mut expression = None;
    let mut projection = None;
    let mut phase = None;
    let mut fixture = None;
    let mut samples = None;
    let mut operations = None;
    let mut values = env::args().skip(1);
    while let Some(name) = values.next() {
        let value = values
            .next()
            .with_context(|| format!("missing value for {name}"))?;
        match name.as_str() {
            "--arm" => arm = Some(value),
            "--cell" => cell = Some(value),
            "--document-class" => document_class = Some(value),
            "--query-family" => query_family = Some(value),
            "--expression" => expression = Some(value),
            "--projection" => projection = Some(value),
            "--phase" => phase = Some(value),
            "--fixture" => fixture = Some(value),
            "--samples" => samples = Some(value.parse().context("samples must be an integer")?),
            "--operations" => {
                operations = Some(value.parse().context("operations must be an integer")?)
            }
            _ => bail!("unsupported argument: {name}"),
        }
    }
    let result = Arguments {
        arm: arm.context("--arm is required")?,
        cell: cell.context("--cell is required")?,
        document_class: document_class.context("--document-class is required")?,
        query_family: query_family.context("--query-family is required")?,
        expression: expression.context("--expression is required")?,
        projection: projection.context("--projection is required")?,
        phase: phase.context("--phase is required")?,
        fixture: fixture.context("--fixture is required")?,
        samples: samples.context("--samples is required")?,
        operations: operations.context("--operations is required")?,
    };
    if result.operations == 0 {
        bail!("operations must be positive");
    }
    Ok(result)
}

fn normalized_text<'a>(values: impl Iterator<Item = &'a str>) -> String {
    values
        .flat_map(str::split_whitespace)
        .collect::<Vec<_>>()
        .join(" ")
}

fn text_value(value: String) -> Value {
    json!({"kind": "text", "value": value})
}

fn attribute_value(name: &str, value: &str) -> Value {
    json!({"kind": "attribute", "value": {"name": name, "value": value}})
}

fn node_value(identifier: &str) -> Value {
    json!({"kind": "node", "value": {"semanticId": identifier}})
}

fn html_selector(projection: &str) -> Result<Selector> {
    let expression = if projection == "text" {
        "article.product[data-selected='true'] span.name"
    } else {
        "article.product[data-selected='true']"
    };
    Selector::parse(expression)
        .map_err(|error| anyhow::anyhow!("invalid control selector: {error:?}"))
}

fn html_values(document: &Html, selector: &Selector, projection: &str) -> Result<Vec<Value>> {
    document
        .select(selector)
        .map(|element| {
            if projection == "text" {
                Ok(text_value(normalized_text(element.text())))
            } else if let Some(name) = projection.strip_prefix("attribute:") {
                let value = element
                    .value()
                    .attr(name)
                    .with_context(|| format!("HTML control match has no {name} attribute"))?;
                Ok(attribute_value(name, value))
            } else if projection == "node" {
                let identifier = element.value().attr("data-id").unwrap_or("selected-node");
                Ok(node_value(identifier))
            } else {
                bail!("unsupported HTML projection: {projection}")
            }
        })
        .collect()
}

fn xml_selected<'a, 'input>(
    document: &'a roxmltree::Document<'input>,
    projection: &str,
) -> Vec<roxmltree::Node<'a, 'input>> {
    let selected = document.descendants().filter(|node| {
        node.is_element()
            && node.tag_name().namespace() == Some("urn:product")
            && node.tag_name().name() == "product"
            && node.attribute("data-selected") == Some("true")
    });
    if projection == "text" {
        selected
            .flat_map(|product| product.children())
            .filter(|node| {
                node.is_element()
                    && node.tag_name().namespace() == Some("urn:product")
                    && node.tag_name().name() == "name"
            })
            .collect()
    } else {
        selected.collect()
    }
}

fn xml_values(document: &roxmltree::Document<'_>, projection: &str) -> Result<Vec<Value>> {
    xml_selected(document, projection)
        .into_iter()
        .map(|node| {
            if projection == "text" {
                Ok(text_value(normalized_text(
                    node.descendants()
                        .filter(|item| item.is_text())
                        .filter_map(|item| item.text()),
                )))
            } else if let Some(name) = projection.strip_prefix("attribute:") {
                let value = node
                    .attribute(name)
                    .with_context(|| format!("XML control match has no {name} attribute"))?;
                Ok(attribute_value(name, value))
            } else if projection == "node" {
                Ok(node_value(
                    node.attribute("data-id").unwrap_or("selected-node"),
                ))
            } else {
                bail!("unsupported XML projection: {projection}")
            }
        })
        .collect()
}

fn json_values(document: &Value, expression: &str) -> Result<Vec<Value>> {
    let selected = if let Some(value) = document.pointer(expression) {
        value.clone()
    } else if expression.starts_with("$.products[") && expression.ends_with("].price") {
        let index = expression
            .trim_start_matches("$.products[")
            .trim_end_matches("].price")
            .parse::<usize>()
            .context("invalid control JSONPath index")?;
        document
            .get("products")
            .and_then(Value::as_array)
            .and_then(|products| products.get(index))
            .and_then(|product| product.get("price"))
            .cloned()
            .context("control JSONPath did not match")?
    } else {
        bail!("unsupported control JSON expression: {expression}")
    };
    Ok(vec![json!({"kind": "json", "value": selected})])
}

fn text_values(text: &str, arguments: &Arguments, compiled: Option<&Regex>) -> Result<Vec<Value>> {
    if arguments.query_family == "textLiteral" {
        return Ok(text
            .match_indices(&arguments.expression)
            .map(|(_, value)| text_value(value.to_owned()))
            .collect());
    }
    let regex = compiled.context("regex control was not compiled")?;
    if let Some(name) = arguments.projection.strip_prefix("captures:") {
        return regex
            .captures_iter(text)
            .map(|captures| {
                let full = captures.get(0).context("regex match has no full capture")?;
                let capture = captures
                    .name(name)
                    .with_context(|| format!("regex match has no {name} capture"))?;
                let values = BTreeMap::from([(name.to_owned(), capture.as_str().to_owned())]);
                Ok(json!({"kind": "text_with_captures", "value": {"text": full.as_str(), "captures": values}}))
            })
            .collect();
    }
    Ok(regex
        .find_iter(text)
        .map(|value| text_value(value.as_str().to_owned()))
        .collect())
}

fn selector(value: &str) -> Result<Selector> {
    Selector::parse(value).map_err(|error| anyhow::anyhow!("invalid record selector: {error:?}"))
}

fn contract_values(text: &str) -> Result<Vec<Value>> {
    let document = Html::parse_document(text);
    let products = selector("article.product")?;
    let names = selector("h2 .name")?;
    let prices = selector("span.price")?;
    let subtitles = selector("span.subtitle")?;
    let categories = selector("span.category")?;
    let mut count = 0_usize;
    let mut first = None;
    let mut last = None;
    for product in document.select(&products) {
        let name = product
            .select(&names)
            .next()
            .map(|node| normalized_text(node.text()))
            .context("control product has no name")?;
        let price = product
            .select(&prices)
            .next()
            .map(|node| normalized_text(node.text()))
            .context("control product has no price")?;
        let numeric = price
            .strip_prefix('$')
            .context("control price has no dollar prefix")?;
        let (whole, cents) = numeric
            .split_once('.')
            .context("control price has no decimal separator")?;
        let _: i64 = whole
            .parse()
            .context("control price whole units are invalid")?;
        if cents.len() != 2 || !cents.bytes().all(|value| value.is_ascii_digit()) {
            bail!("control price cents are invalid")
        }
        let _subtitle = product
            .select(&subtitles)
            .next()
            .map(|node| normalized_text(node.text()));
        let _categories = product
            .select(&categories)
            .map(|node| normalized_text(node.text()))
            .collect::<Vec<_>>();
        if first.is_none() {
            first = Some(name.clone());
        }
        last = Some(name);
        count = count
            .checked_add(1)
            .context("control record count overflow")?;
    }
    Ok(vec![
        json!({"kind": "records", "value": {"count": count, "first": first, "last": last}}),
    ])
}

fn values_for(data: &[u8], arguments: &Arguments) -> Result<Vec<Value>> {
    match arguments.document_class.as_str() {
        "contractHtml" => contract_values(std::str::from_utf8(data)?),
        "sourceHtml" => {
            let selector = html_selector(&arguments.projection)?;
            html_values(
                &Html::parse_document(std::str::from_utf8(data)?),
                &selector,
                &arguments.projection,
            )
        }
        "sourceXml" => xml_values(
            &roxmltree::Document::parse(std::str::from_utf8(data)?)?,
            &arguments.projection,
        ),
        "sourceJson" => json_values(&serde_json::from_slice(data)?, &arguments.expression),
        "sourceText" => {
            let compiled = if arguments.query_family == "regex" {
                Some(Regex::new(&arguments.expression)?)
            } else {
                None
            };
            text_values(std::str::from_utf8(data)?, arguments, compiled.as_ref())
        }
        value => bail!("unsupported control document class: {value}"),
    }
}

fn measured_values(data: &[u8], arguments: &Arguments) -> Result<(Vec<Value>, Vec<u64>)> {
    let expected = values_for(data, arguments)?;
    let text = std::str::from_utf8(data)?;
    let html_selector = if arguments.document_class == "sourceHtml" {
        Some(html_selector(&arguments.projection)?)
    } else {
        None
    };
    let regex = if arguments.query_family == "regex" {
        Some(Regex::new(&arguments.expression)?)
    } else {
        None
    };
    let parsed_html = if arguments.document_class == "sourceHtml" && arguments.phase == "locate" {
        Some(Html::parse_document(text))
    } else {
        None
    };
    let parsed_xml = if arguments.document_class == "sourceXml" && arguments.phase == "locate" {
        Some(roxmltree::Document::parse(text)?)
    } else {
        None
    };
    let parsed_json = if arguments.document_class == "sourceJson" && arguments.phase == "locate" {
        Some(serde_json::from_slice::<Value>(data)?)
    } else {
        None
    };

    let mut timings = Vec::with_capacity(arguments.samples);
    let mut last = expected.clone();
    for _ in 0..arguments.samples {
        let started = Instant::now();
        for _ in 0..arguments.operations {
            match arguments.phase.as_str() {
                "parse" => match arguments.document_class.as_str() {
                    "sourceHtml" => {
                        black_box(Html::parse_document(black_box(text)));
                    }
                    "sourceXml" => {
                        black_box(roxmltree::Document::parse(black_box(text))?);
                    }
                    "sourceJson" => {
                        black_box(serde_json::from_slice::<Value>(black_box(data))?);
                    }
                    "sourceText" => {
                        black_box(std::str::from_utf8(black_box(data))?);
                    }
                    value => bail!("unsupported parse document class: {value}"),
                },
                "locate" => {
                    last = match arguments.document_class.as_str() {
                        "sourceHtml" => html_values(
                            parsed_html.as_ref().context("parsed HTML is missing")?,
                            html_selector.as_ref().context("HTML selector is missing")?,
                            &arguments.projection,
                        )?,
                        "sourceXml" => xml_values(
                            parsed_xml.as_ref().context("parsed XML is missing")?,
                            &arguments.projection,
                        )?,
                        "sourceJson" => json_values(
                            parsed_json.as_ref().context("parsed JSON is missing")?,
                            &arguments.expression,
                        )?,
                        "sourceText" => text_values(text, arguments, regex.as_ref())?,
                        value => bail!("unsupported locate document class: {value}"),
                    };
                }
                "endToEnd" => {
                    last = values_for(data, arguments)?;
                }
                value => bail!("unsupported phase: {value}"),
            }
            black_box(&last);
        }
        let elapsed = started.elapsed().as_nanos()
            / u128::try_from(arguments.operations).context("operation count does not fit u128")?;
        timings.push(u64::try_from(elapsed).context("elapsed nanoseconds do not fit u64")?);
    }
    if last != expected {
        bail!("control output changed during measurement")
    }
    Ok((expected, timings))
}

fn main() -> Result<()> {
    let arguments = arguments()?;
    let data = fs::read(&arguments.fixture)
        .with_context(|| format!("failed to read {}", arguments.fixture))?;
    let (values, samples_ns) = measured_values(&data, &arguments)?;
    let encoded = serde_json::to_vec(&values)?;
    let output = Output {
        schema_version: "yosoi.benchmark.diagnostic-result.v2",
        arm_id: arguments.arm,
        cell_id: arguments.cell,
        document_class: arguments.document_class,
        query_family: arguments.query_family,
        projection: arguments.projection,
        phase: arguments.phase,
        terminal_status: "ok",
        match_count: values.len(),
        values,
        output_sha256: format!("{:x}", Sha256::digest(encoded)),
        samples_ns,
        operations_per_sample: arguments.operations,
        input_bytes: data.len(),
    };
    println!("{}", serde_json::to_string(&output)?);
    Ok(())
}
