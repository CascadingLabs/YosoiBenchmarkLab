use std::{env, fs, hint::black_box, time::Instant};

use anyhow::{Context, Result, bail};
use serde::Serialize;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use yosoi::prelude as ys;
use yosoi_documents::prelude as yd;
use yosoi_documents::{ResourceBudget, ResourceBudgetValues};

#[derive(Debug)]
struct Arguments {
    cell: String,
    document_class: String,
    query_family: String,
    expression: String,
    projection: String,
    phase: String,
    fixture: String,
    samples: usize,
    operations: usize,
    namespace_prefix: Option<String>,
    namespace_uri: Option<String>,
    max_matches: Option<u64>,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct Output {
    schema_version: &'static str,
    arm_id: &'static str,
    source_revision: &'static str,
    cell_id: String,
    document_class: String,
    query_family: String,
    projection: String,
    phase: String,
    terminal_status: &'static str,
    match_count: usize,
    record_count: Option<usize>,
    values: Vec<Value>,
    output_sha256: String,
    samples_ns: Vec<u64>,
    operations_per_sample: usize,
    input_bytes: usize,
}

const PRODUCT_ROOT: ys::PinnedLocator = ys::locator::css("article.product");
const PRODUCT_NAME: ys::PinnedOutputLocator = ys::locator::css(".name").text();
const PRODUCT_PRICE: ys::PinnedOutputLocator = ys::locator::css("span.price").text();
const PRODUCT_SUBTITLE: ys::PinnedOutputLocator = ys::locator::css("span.subtitle").text();
const PRODUCT_CATEGORY: ys::PinnedOutputLocator = ys::locator::css("span.category").text();

#[derive(ys::Contract)]
#[ys(
    id = "v2_product",
    description = "One product in the V2 diagnostic catalog",
    root = PRODUCT_ROOT
)]
struct Product {
    #[ys(description = "Product name", locator = PRODUCT_NAME)]
    name: String,
    #[ys(description = "Product price", locator = PRODUCT_PRICE)]
    price: ys::Money,
    #[ys(description = "Supporting description", locator = PRODUCT_SUBTITLE)]
    subtitle: Option<String>,
    #[ys(description = "Product categories", locator = PRODUCT_CATEGORY)]
    categories: Vec<String>,
}

#[derive(ys::Contract)]
#[ys(
    id = "v2_xml_product",
    description = "One product in the V2 XML diagnostic catalog",
    root = ys::locator::css("product")
)]
struct XmlProduct {
    #[ys(description = "Product name", locator = ys::locator::css("name").text())]
    name: String,
    #[ys(description = "Product price", locator = ys::locator::css("price").text())]
    price: ys::Money,
}

#[derive(ys::Contract)]
#[ys(id = "v2_text_summary", description = "The selected V2 text record")]
struct TextSummary {
    #[ys(
        description = "Selected order",
        locator = ys::locator::text_literal("ORDER-000017").text()
    )]
    label: String,
}

#[derive(ys::Contract)]
#[ys(
    id = "v2_ax_summary",
    description = "The selected V2 accessibility record"
)]
struct AxSummary {
    #[ys(
        description = "Selected accessible label",
        locator = ys::locator::text_literal("Buy p-000017").text()
    )]
    label: String,
}

#[allow(dead_code)] // The rejected native JSON value intentionally never becomes this String field.
#[derive(ys::Contract)]
#[ys(id = "v2_json_summary", description = "The selected V2 JSON value")]
struct JsonSummary {
    #[ys(
        description = "Selected JSON price",
        locator = ys::locator::text_literal("unused-json-price").text()
    )]
    value: String,
}

fn arguments() -> Result<Arguments> {
    let mut cell = None;
    let mut document_class = None;
    let mut query_family = None;
    let mut expression = None;
    let mut projection = None;
    let mut phase = None;
    let mut fixture = None;
    let mut samples = None;
    let mut operations = None;
    let mut namespace_prefix = None;
    let mut namespace_uri = None;
    let mut max_matches = None;
    let mut values = env::args().skip(1);
    while let Some(name) = values.next() {
        let value = values
            .next()
            .with_context(|| format!("missing value for {name}"))?;
        match name.as_str() {
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
            "--namespace-prefix" => namespace_prefix = Some(value),
            "--namespace-uri" => namespace_uri = Some(value),
            "--max-matches" => {
                max_matches = Some(value.parse().context("max matches must be an integer")?)
            }
            _ => bail!("unsupported argument: {name}"),
        }
    }
    let result = Arguments {
        cell: cell.context("--cell is required")?,
        document_class: document_class.context("--document-class is required")?,
        query_family: query_family.context("--query-family is required")?,
        expression: expression.context("--expression is required")?,
        projection: projection.context("--projection is required")?,
        phase: phase.context("--phase is required")?,
        fixture: fixture.context("--fixture is required")?,
        samples: samples.context("--samples is required")?,
        operations: operations.context("--operations is required")?,
        namespace_prefix,
        namespace_uri,
        max_matches,
    };
    if result.operations == 0 {
        bail!("operations must be positive");
    }
    if result.namespace_prefix.is_some() != result.namespace_uri.is_some() {
        bail!("namespace prefix and URI must be provided together");
    }
    Ok(result)
}

fn document(arguments: &Arguments, data: Vec<u8>) -> Result<yd::Document> {
    match arguments.document_class.as_str() {
        "sourceHtml" => Ok(yd::Document::html("v2.html", data)?),
        "sourceXml" => Ok(yd::Document::xml("v2.xml", data)?),
        "sourceJson" => Ok(yd::Document::json("v2.json", data)?),
        "sourceText" => Ok(yd::Document::text("v2.txt", data)?),
        "renderedDom" => Ok(yd::Document::rendered_dom(
            "v2.dom.json",
            yd::DocumentEpoch::try_from(1)?,
            data,
        )?),
        "accessibilityTree" => Ok(yd::Document::accessibility_tree(
            "v2.ax.json",
            yd::DocumentEpoch::try_from(1)?,
            data,
        )?),
        value => bail!("unsupported document class: {value}"),
    }
}

fn query(arguments: &Arguments) -> Result<yd::QuerySpec> {
    let mut query = match arguments.query_family.as_str() {
        "css" => yd::css(&arguments.expression)?,
        "xpath" => yd::xpath(&arguments.expression)?,
        "treeText" => yd::tree_text_contains(&arguments.expression)?,
        "jsonPointer" => yd::json_pointer(&arguments.expression)?,
        "jsonPath" => yd::json_path(&arguments.expression)?,
        "textLiteral" => yd::text_literal(&arguments.expression)?,
        "regex" => yd::regex(&arguments.expression)?,
        "role" => yd::role(&arguments.expression)?,
        "accessibleName" => yd::accessible_name(&arguments.expression)?,
        "accessibilityText" => yd::accessibility_text(&arguments.expression)?,
        "stateExpanded" => yd::accessibility_state(
            yd::AccessibilityStateName::Expanded,
            arguments
                .expression
                .parse()
                .context("state expression must be true or false")?,
        ),
        value => bail!("unsupported query family: {value}"),
    };
    if let (Some(prefix), Some(uri)) = (&arguments.namespace_prefix, &arguments.namespace_uri) {
        query = query.with_namespace(prefix, uri)?;
    }
    Ok(query)
}

fn plan(arguments: &Arguments) -> Result<yd::Plan> {
    let query = query(arguments)?;
    let projected = if arguments.projection == "text" || arguments.projection == "accessibilityText"
    {
        query.text()
    } else if let Some(name) = arguments.projection.strip_prefix("attribute:") {
        query.attribute(name)?
    } else if arguments.projection == "node" {
        query.node()
    } else if arguments.projection == "value" {
        query.value()
    } else if let Some(name) = arguments.projection.strip_prefix("captures:") {
        query.captures([name])?
    } else if arguments.projection == "accessibleName" {
        query.name()
    } else {
        bail!("unsupported projection: {}", arguments.projection)
    };
    Ok(yd::Plan::new([yd::output("result", projected)?])?)
}

fn values(outcome: yd::LocateOutcome) -> Result<Vec<Value>> {
    match outcome {
        yd::LocateOutcome::Matched { result } => result
            .findings()
            .iter()
            .map(|finding| serde_json::to_value(finding.value()).map_err(Into::into))
            .collect(),
        yd::LocateOutcome::NoMatch { .. } => Ok(Vec::new()),
        yd::LocateOutcome::Indeterminate {
            completeness,
            reason_code,
            ..
        } => bail!("indeterminate result: {reason_code} ({completeness:?})"),
        yd::LocateOutcome::Failed { failure } => bail!("locate failed: {failure:?}"),
    }
}

fn elapsed_per_operation(started: Instant, operations: usize) -> Result<u64> {
    let divisor = u128::try_from(operations).context("operation count does not fit u128")?;
    let elapsed = started.elapsed().as_nanos() / divisor;
    u64::try_from(elapsed).context("elapsed nanoseconds do not fit u64")
}

fn budget(arguments: &Arguments) -> Result<ResourceBudget> {
    let default = ResourceBudget::default();
    Ok(ResourceBudget::try_new(ResourceBudgetValues {
        max_input_bytes: default.max_input_bytes(),
        max_nodes: default.max_nodes(),
        max_selector_visits: default.max_selector_visits(),
        max_query_bytes: default.max_query_bytes(),
        max_query_steps: default.max_query_steps(),
        max_regions: default.max_regions(),
        max_matches: arguments.max_matches.unwrap_or(default.max_matches()),
        max_captures: default.max_captures(),
        max_depth: default.max_depth(),
        max_output_bytes: default.max_output_bytes(),
    })?)
}

fn measure_document(
    document: &yd::Document,
    compiled_plan: &yd::Plan,
    arguments: &Arguments,
) -> Result<(Vec<Value>, Vec<u64>)> {
    let budget = budget(arguments)?;
    let expected = values(document.locate_with_budget(compiled_plan, budget))?;
    let parsed = if arguments.phase == "locate" {
        Some(document.parse_with_budget(budget)?)
    } else {
        None
    };
    let mut timings = Vec::with_capacity(arguments.samples);
    let mut last = expected.clone();
    for _ in 0..arguments.samples {
        let started = Instant::now();
        for _ in 0..arguments.operations {
            match arguments.phase.as_str() {
                "queryBuild" => {
                    black_box(plan(arguments)?);
                }
                "parse" => {
                    black_box(document.parse_with_budget(budget)?);
                }
                "locate" => {
                    last = values(
                        parsed
                            .as_ref()
                            .context("parsed document is missing")?
                            .locate(compiled_plan),
                    )?;
                }
                "endToEnd" => {
                    last = values(document.locate_with_budget(compiled_plan, budget))?;
                }
                value => bail!("unsupported document phase: {value}"),
            }
            black_box(&last);
        }
        timings.push(elapsed_per_operation(started, arguments.operations)?);
    }
    if last != expected {
        bail!("Yosoi output changed during measurement")
    }
    Ok((expected, timings))
}

fn record_summary(records: &[Product]) -> Value {
    json!({
        "kind": "records",
        "value": {
            "count": records.len(),
            "first": records.first().map(|record| record.name.as_str()),
            "last": records.last().map(|record| record.name.as_str()),
            "firstPriceMinorUnits": records.first().map(|record| record.price.minor_units()),
            "firstSubtitle": records.first().and_then(|record| record.subtitle.as_deref()),
            "firstCategoryCount": records.first().map(|record| record.categories.len()),
        }
    })
}

fn xml_record_summary(records: &[XmlProduct]) -> Value {
    json!({
        "kind": "records",
        "value": {
            "count": records.len(),
            "first": records.first().map(|record| record.name.as_str()),
            "last": records.last().map(|record| record.name.as_str()),
            "firstPriceMinorUnits": records.first().map(|record| record.price.minor_units()),
        }
    })
}

fn label_summary(label: Option<&str>, count: usize) -> Value {
    json!({"kind": "records", "value": {"count": count, "first": label, "last": label}})
}

fn complete_records(document: &ys::Document) -> Result<Vec<Product>> {
    Ok(Product::extract(&Product::locate(document)?)
        .validate()
        .require_all()?)
}

fn complete_xml_records(document: &ys::Document) -> Result<Vec<XmlProduct>> {
    Ok(XmlProduct::extract(&XmlProduct::locate(document)?)
        .validate()
        .require_all()?)
}

fn complete_text_records(document: &ys::Document) -> Result<Vec<TextSummary>> {
    Ok(TextSummary::extract(&TextSummary::locate(document)?)
        .validate()
        .require_all()?)
}

fn complete_ax_records(document: &ys::Document) -> Result<Vec<AxSummary>> {
    let plan = ys::Plan::new([ys::output(
        "label",
        ys::accessible_name("Buy p-000017")?.name(),
    )?])?;
    let located = document.locate(&plan);
    Ok(AxSummary::extract(&located).validate().require_all()?)
}

fn rejected_json_summary(document: &ys::Document) -> Result<(usize, usize)> {
    let plan = ys::Plan::new([ys::output(
        "value",
        ys::json_pointer("/products/17/price")?.value(),
    )?])?;
    let located = document.locate(&plan);
    match JsonSummary::extract(&located).validate() {
        ys::ContractOutcome::Evaluated {
            records, issues, ..
        } => Ok((records.len(), issues.len())),
        outcome => bail!("expected evaluated rejected JSON summary, got {outcome:?}"),
    }
}

fn measure_contracts(
    document: &ys::Document,
    arguments: &Arguments,
) -> Result<(Vec<Value>, usize, Vec<u64>)> {
    let expected_records = complete_records(document)?;
    let expected_values = vec![record_summary(&expected_records)];
    let located = Product::locate(document)?;
    let mut timings = Vec::with_capacity(arguments.samples);
    let mut last_count = expected_records.len();

    for _ in 0..arguments.samples {
        let started = Instant::now();
        for _ in 0..arguments.operations {
            last_count = match arguments.phase.as_str() {
                "planCached" => {
                    black_box(Product::plan()?);
                    expected_records.len()
                }
                "locate" => {
                    black_box(Product::locate(document)?);
                    expected_records.len()
                }
                "extract" => {
                    let extracted = black_box(Product::extract(&located));
                    extracted.candidates().len()
                }
                "extractValidate" => {
                    let validated = black_box(Product::extract(&located).validate());
                    match validated {
                        ys::ContractOutcome::Evaluated { records, .. } => records.len(),
                        _ => 0,
                    }
                }
                "extractValidateRequireAll" => {
                    black_box(Product::extract(&located).validate().require_all()?).len()
                }
                "endToEnd" => black_box(complete_records(document)?).len(),
                value => bail!("unsupported contract phase: {value}"),
            };
        }
        timings.push(elapsed_per_operation(started, arguments.operations)?);
    }
    if last_count != expected_records.len() {
        bail!("contract record count changed during measurement")
    }
    Ok((expected_values, expected_records.len(), timings))
}

fn measure_compatibility_contract(
    document: &ys::Document,
    arguments: &Arguments,
) -> Result<(Vec<Value>, usize, Vec<u64>)> {
    let (expected_values, expected_count) = match arguments.cell.as_str() {
        "contracts.xml.products" => {
            let records = complete_xml_records(document)?;
            (vec![xml_record_summary(&records)], records.len())
        }
        "contracts.text.summary" => {
            let records = complete_text_records(document)?;
            let label = records.first().map(|record| record.label.as_str());
            (vec![label_summary(label, records.len())], records.len())
        }
        "contracts.dom.products" => {
            let records = complete_records(document)?;
            (vec![record_summary(&records)], records.len())
        }
        "contracts.ax.summary" => {
            let records = complete_ax_records(document)?;
            let label = records.first().map(|record| record.label.as_str());
            (vec![label_summary(label, records.len())], records.len())
        }
        "contracts.json.rejection" => {
            let (records, issues) = rejected_json_summary(document)?;
            (
                vec![
                    json!({"kind": "rejected_records", "value": {"records": records, "issues": issues}}),
                ],
                records,
            )
        }
        value => bail!("unsupported compatibility contract lane: {value}"),
    };
    let mut timings = Vec::with_capacity(arguments.samples);
    let mut last_count = expected_count;
    for _ in 0..arguments.samples {
        let started = Instant::now();
        for _ in 0..arguments.operations {
            last_count = match arguments.cell.as_str() {
                "contracts.xml.products" => black_box(complete_xml_records(document)?).len(),
                "contracts.text.summary" => black_box(complete_text_records(document)?).len(),
                "contracts.dom.products" => black_box(complete_records(document)?).len(),
                "contracts.ax.summary" => black_box(complete_ax_records(document)?).len(),
                "contracts.json.rejection" => {
                    let (records, issues) = black_box(rejected_json_summary(document)?);
                    if issues != 1 {
                        bail!("JSON rejection issue count changed")
                    }
                    records
                }
                value => bail!("unsupported compatibility contract lane: {value}"),
            };
        }
        timings.push(elapsed_per_operation(started, arguments.operations)?);
    }
    if last_count != expected_count {
        bail!("compatibility contract record count changed during measurement")
    }
    Ok((expected_values, expected_count, timings))
}

fn contract_document(arguments: &Arguments, data: Vec<u8>) -> Result<ys::Document> {
    match arguments.document_class.as_str() {
        "contractHtml" | "sourceHtml" => Ok(ys::Document::html("v2-contracts.html", data)?),
        "sourceXml" => Ok(ys::Document::xml("v2-contracts.xml", data)?),
        "sourceJson" => Ok(ys::Document::json("v2-contracts.json", data)?),
        "sourceText" => Ok(ys::Document::text("v2-contracts.txt", data)?),
        "renderedDom" => Ok(ys::Document::rendered_dom(
            "v2-contracts.dom.json",
            ys::DocumentEpoch::try_from(1)?,
            data,
        )?),
        "accessibilityTree" => Ok(ys::Document::accessibility_tree(
            "v2-contracts.ax.json",
            ys::DocumentEpoch::try_from(1)?,
            data,
        )?),
        value => bail!("unsupported contract document class: {value}"),
    }
}

fn resource_bounded_value(outcome: ys::LocateOutcome) -> Result<Value> {
    match outcome {
        ys::LocateOutcome::Failed { failure } => {
            let diagnostic = format!("{failure:?}");
            if !diagnostic.contains("LimitExhausted") {
                bail!("expected a resource limit failure, got {diagnostic}")
            }
            Ok(json!({"kind": "resource_bounded", "value": {"failure": diagnostic}}))
        }
        outcome => bail!("expected a resource-bounded locate outcome, got {outcome:?}"),
    }
}

fn measure_resource_bounded(
    document: &ys::Document,
    plan: &ys::Plan,
    arguments: &Arguments,
) -> Result<(Vec<Value>, usize, Vec<u64>)> {
    let expected = resource_bounded_value(document.locate(plan))?;
    let mut timings = Vec::with_capacity(arguments.samples);
    for _ in 0..arguments.samples {
        let started = Instant::now();
        for _ in 0..arguments.operations {
            black_box(resource_bounded_value(document.locate(plan))?);
        }
        timings.push(elapsed_per_operation(started, arguments.operations)?);
    }
    Ok((vec![expected], 0, timings))
}

fn main() -> Result<()> {
    let arguments = arguments()?;
    let data = fs::read(&arguments.fixture)
        .with_context(|| format!("failed to read {}", arguments.fixture))?;
    let (values, record_count, samples_ns) = if arguments.phase == "resourceBounded" {
        let contract_document = contract_document(&arguments, data.clone())?;
        let contract_plan = if arguments.cell == "contracts.xml.products" {
            XmlProduct::plan()?
        } else {
            Product::plan()?
        };
        let (values, count, samples) =
            measure_resource_bounded(&contract_document, contract_plan, &arguments)?;
        (values, Some(count), samples)
    } else if arguments.cell == "contracts.html.products" {
        let contract_document = contract_document(&arguments, data.clone())?;
        let (values, count, samples) = measure_contracts(&contract_document, &arguments)?;
        (values, Some(count), samples)
    } else if arguments.cell.starts_with("contracts.") {
        let contract_document = contract_document(&arguments, data.clone())?;
        let (values, count, samples) =
            measure_compatibility_contract(&contract_document, &arguments)?;
        (values, Some(count), samples)
    } else {
        let document = document(&arguments, data.clone())?;
        let plan = plan(&arguments)?;
        let (values, samples) = measure_document(&document, &plan, &arguments)?;
        (values, None, samples)
    };
    let encoded = serde_json::to_vec(&values)?;
    let output = Output {
        schema_version: "yosoi.benchmark.diagnostic-result.v2",
        arm_id: "yosoiRust",
        source_revision: option_env!("YOSOI_SOURCE_REVISION").unwrap_or("unknown"),
        cell_id: arguments.cell,
        document_class: arguments.document_class,
        query_family: arguments.query_family,
        projection: arguments.projection,
        phase: arguments.phase,
        terminal_status: "ok",
        match_count: values.len(),
        record_count,
        values,
        output_sha256: format!("{:x}", Sha256::digest(encoded)),
        samples_ns,
        operations_per_sample: arguments.operations,
        input_bytes: data.len(),
    };
    println!("{}", serde_json::to_string(&output)?);
    Ok(())
}
