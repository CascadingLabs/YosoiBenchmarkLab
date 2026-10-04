# Decision 0003: start fully offline with parsers

Current evidence: [2026-10-04 benchmark results](../current-results.md).
The latest run includes the ranked `lol_html` caveman control and retained
resource-stopped browser cells.

Status: accepted.

The first implementation slice is the parser/selector specification and corpus.
It requires no browser, public URL, hosted service, credential, or competitor
installation.

HTTP frameworks follow only after this contract and result protocol are stable.
Rendered browser Requests follow HTTP. This ordering minimizes operational noise
while the scientific contract is still changing.
