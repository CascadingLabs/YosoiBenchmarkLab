# Benchmark Lab working rules

## Repository firewall

- This repository is independent from Yosoi and must not become a Yosoi
  workspace member, submodule, nested checkout, vendored directory, path
  dependency, or shared build environment.
- Competitor code and dependencies live only here, in arm-specific locked
  environments.
- Consume Yosoi only as an immutable built release artifact.

## Scope

- Required quadrants are parser/selector engines, HTTP scraping frameworks,
  and rendered browser Requests, in that order.
- Browser automation, hosted APIs, paid services, and hosted-only capabilities
  are out of scope.
- The public caveman lane is pure Rust. Python and Node binding overhead is a
  separate internal diagnostic.

## Evidence

- Freeze inputs, operations, outputs, defaults, versions, and scoring before a
  comparative run.
- Correctness and output equivalence gate speed rankings.
- Retain failures and raw distributions; never publish only the best run.
- Treat parse-only, locate-only, end-to-end, cold startup, CPU, RSS, and
  allocation evidence as distinct measurements.
- Do not infer one metric from another.

## Resource safety

- Before builds, tests, dependency installation, or benchmark runs, inspect
  `free -h` and the resident-memory process view.
- Run only one expensive command at a time and default every tool to one worker.
- Stop work that unexpectedly fans out, consumes several GiB of aggregate RSS,
  drives available memory sharply down, or increases swap pressure.
- Never call a stopped or skipped validation successful.

## Parser slice

- Parser fixtures and scoring must run without network access.
- Locator contracts use the typed neutral vocabulary in the benchmark spec,
  not a shared raw CSS/XPath string that privileges one API.
- Adapters may compile the neutral locator into a native query, but must record
  the effective operation and prove exact output before timing.
