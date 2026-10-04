# Decision 0002: the public caveman result is pure Rust

Status: accepted.

The public Yosoi caveman arm uses the public Rust surface or a tiny Rust release
binary. It does not include Python or Node binding overhead.

Python and future Node bindings reuse the same inputs and oracle in a separate
internal Yosoi-versus-Yosoi suite. That suite measures import/startup, warm call,
argument conversion, result materialization, and optional public serialization
without changing the Rust headline.
