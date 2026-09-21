---
name: adx-dev
description: Develop Agent DX code with TDD, targeted Rust/Go/Python checks, multi-worktree build caches and coherent release packages; use for ADX source changes, local cache or disk-growth work, builds and commits, while live deployment and CI operations use their dedicated skills.
---

# ADX Development

Read the selected checkout's `AGENTS.md`, current branch/commit, worktree status and relevant module before editing. Preserve unrelated changes. Use a clean worktree when isolation is needed; do not assume a specific local path or turn a dirty checkout into a clean one by resetting it.

## Ownership

- `agent/`: Agent API, sessions and orchestration. Platform access belongs behind the public Sandbox SDK.
- `platform/control-plane/`: Rust Master, Node Manager and `adxctl`; small Go Sandbox API adapter.
- `platform/crates/`: Instance model, protocol, discovery, Filter/Score scheduling.
- `gateway/`: shared Edge, Node Proxy and forwarding. Data requests do not enter Instance lifecycle queues.
- `platform/runtime/rrt/`: instance-local HTTP operations and runtime cooperation.
- `platform/sdk/sandbox/`: `adx-sandbox` distribution, `adx_sandbox` import, `ADX_*` configuration.

The current Global scheduler rotates across in-process Domains; Domain queues and Filter/Score choose nodes; Node Manager performs final local admission and owns per-Instance serial lifecycle tasks. Verify current implementation before changing these boundaries.

Internal APIs use Instance. Only `frontend_proxy_service.proto` retains its necessary legacy compatibility dependencies. RRT uses HTTP; do not reintroduce POSIX/function/RuntimeRPC services to satisfy a helper dependency. RuntimeBackend currently adapts external sandboxd; Start returns a backend ID distinct from the platform identity.

## TDD and implementation

For a behavioral change, first exercise the failing contract at its owning layer. Use real Socket/Redis or end-to-end checks when the bug concerns cross-process ordering, routing, persistence or cleanup. Avoid adding a test that merely restates the implementation. Preserve generation, ownership and result-publication checks during retries.

Read [build and package commands](references/build.md) for builds. Prefer the project's Makefile and `build/ci/run.py`; keep outputs under caller-owned `out/` or configured caches. Check `rust-toolchain.toml`, Go module requirements and Python metadata instead of assuming the recorded baseline is current.

For local Rust work across Git worktrees, share compiler results without mixing release identity. Prefer the repository's `build/cache/cargo_cache.py` and `make cargo-cache-info` when present: ordinary build/check/test work may use the host-and-toolchain-keyed shared target with `CARGO_INCREMENTAL=0`, plus a shared size-bounded sccache when installed. Use an isolated target for release/package assembly, binaries that will keep running after the build, or worktrees that must compile concurrently. An explicit caller or CI `CARGO_TARGET_DIR` always wins. Do not point every worktree at an unkeyed `target/debug`, and do not clean a shared target while Cargo or rustc is active.

When disk growth is the task, attribute `debug/incremental`, `debug/deps`, worktree-local targets and sccache separately. Treat target and sccache entries as reproducible but not automatically authorized for deletion. Resolve exact directories, active processes and cache identity first; use the repository status helper or bounded `du`, then clean only the requested inactive scope and remeasure filesystem space.

For long builds/tests/packaging, assign a narrow-context execution worker when available and authorized: absolute repo, exact command, concurrency, success criteria and log path. No source edits by the worker. Save full output; monitor at 60–180 seconds and return only progress, first error, useful tail, verdict and artifact paths. Do not duplicate its polling from the parent.

After relevant checks pass, stop expanding tests without a new change or unresolved concern. Component tests, RRT interoperability, process smoke and full public SDK E2E are separate evidence layers.

## Commit and handoff

Follow target-repository commit conventions, normally conventional subject plus one Signed-off-by. Inspect staged diff and `git diff --check`. Push/create PR only within the user's authorized scope; verify the configured remote and account. Do not inherit unrelated protected-repository bot commands from another toolkit.

Report changed behavior, tests and exact limitations. For release/deployment handoff include commit, dirty state, target/profile, package manifest and hashes. Record planned features separately from usable service wiring. SDK API presence alone does not prove the new backend supports that operation.
