# Rerun the complete Benchmark Lab

Run all three comparative quadrants and the separate V2 diagnostics against
one frozen Yosoi source snapshot. Use one build worker and run the commands
serially. The runners retain the existing seeded campaign order, fixtures,
sample counts, correctness oracles, and control-equivalence boundaries.

## Prepare isolated environments

Create scratch space on disk outside both repositories. `/tmp` may be a
memory-backed filesystem; avoid placing multi-gigabyte build trees there.
Run these commands from the lab root:

```bash
benchmarkWork=$(mktemp -d "$PWD/../.benchmark-run.XXXXXX")
for group in parser http browser; do
  UV_PROJECT_ENVIRONMENT="$benchmarkWork/python-$group" \
    UV_CONCURRENT_BUILDS=1 UV_CONCURRENT_DOWNLOADS=1 UV_CONCURRENT_INSTALLS=1 \
    uv sync --frozen --only-group "$group" --python 3.13
done

for quadrant in http browser; do
  (cd "adapters/$quadrant/node-crawlee" && \
    PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm ci --no-audit --no-fund)
done
```

Use a regular Stable Chrome or Chromium executable for every rendered arm.
Record its version, executable SHA-256, and distribution package SHA-256.
Testing-only browser distributions are excluded. Preserve the browser's
sandbox and site isolation.

## Freeze and build current Yosoi

```bash
python3 tools/buildCurrentYosoi.py \
  --yosoi-repository ../Yosoi \
  --revision @ \
  --work "$benchmarkWork" \
  --output "$benchmarkWork/artifacts" \
  --offline
```

The builder snapshots the requested JJ revision, exports its Git archive, and
builds all four lab adapters outside both repositories. `@` includes the current
tracked working-copy changes. The builder records the exact commit and archive
digest; later commands must reuse that same snapshot. It refuses to substitute
a different revision into an existing work directory. The Yosoi checkout is
not edited. Source-archive builds are local diagnostic artifacts, not published
Yosoi releases.

Rust uses 1.99.0 with one Cargo job. Each adapter begins with the frozen Yosoi
Cargo lock and retains its resulting lockfile and digest. Omit `--offline` only
when required dependencies are missing from the local registry cache.

## Run every lane

```bash
python3 tools/runCurrentBenchmark.py \
  --work "$benchmarkWork" \
  --python-parser "$benchmarkWork/python-parser/bin/python" \
  --python-http "$benchmarkWork/python-http/bin/python" \
  --python-browser "$benchmarkWork/python-browser/bin/python" \
  --chromium /path/to/regular-stable-chrome
```

The command serially builds locked controls, runs the ten-arm caveman matrix
(including `lol_html`),
the seven-arm repeated hard matrix, the nine-arm smoke/resource pass, five
Criterion campaigns per Rust arm, all HTTP and rendered concurrency cells,
and every V2 matrix, extraction, conformance, negative, and resource-bound lane.
The two Beautiful Soup hard-catalog observations remain single samples under
the established resource-bounded protocol.

Rendered adapters have a 180-second deadline and a 3 GiB aggregate sampled RSS
cap. A stopped adapter and its owned descendants are terminated and its outcome
is retained. A browser cell receives timing medians only when all three
campaigns pass exact output and cleanup. Failed or resource-stopped cells have
no speed ranking; the report must state their outcomes.

`--sections build,parser,criterion,http,browser,v2` is the default. A completed
lane's summary is reused when resuming the same snapshot; partial lanes rerun
into their scratch destinations. Preserve failed attempts separately before
resuming. Do not reuse a successful summary after changing an artifact,
fixture, compiler, or adapter.

## Seal and verify

Retain a new dated evidence directory for each quadrant and V2. Keep earlier
bundles byte-for-byte unchanged. Use `tools/compileExploratoryReport.py` with
`--captured-on` for the parser report and `tools/compileV2Report.py` for V2.
Seal HTTP/browser raw records, summaries, identities, environment metadata,
and reports with byte counts and SHA-256 manifests.

Create a baseline register pointing to those manifest digests, then verify:

```bash
python3 tools/verifyBaseline.py --baseline evidence/current.json
python3 tools/verifyV2.py --evidence evidence/YYYY-MM-DD-diagnostics-v2
```

Update the README and current-results documentation only after those gates
pass. Record omitted, failed, unsupported, or resource-stopped work explicitly.
Timing, sampled process RSS, CPU, package size, and allocation evidence remain
different measurements. Compare current arms collected together; comparisons
to a previous host, browser, compiler, or dependency set are historical context.
