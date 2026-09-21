# Build and package reference

Run from the selected ADX root. Inspect these inputs before invoking commands:

- `rust-toolchain.toml`, `Cargo.toml`, `Cargo.lock`
- `platform/control-plane/sandbox-api/go.mod`, `build/codegen/go.sh`
- Python package metadata under `agent/` and `platform/sdk/sandbox/python/`
- `Makefile`, `build/ci/run.py`, `build/release/build.sh`

At the recorded baseline Rust is 1.95.0, the Go module requires 1.24.1+, CI uses Go 1.25.5, Sandbox SDK requires Python 3.10+, Redis is 7.2.5. Go generators are pinned in `build/codegen/go.sh`. Treat the checkout as authoritative.

## Cache and targeted checks

Choose existing compatible caches. In automation persist Cargo downloads/git state, target outputs, GOCACHE and GOMODCACHE; separate incompatible targets/toolchains and serialize writers that assemble release binaries. Do not use `cargo clean` as a routine retry.

Current checkouts with `build/cache/cargo_cache.py` resolve all Git worktrees to a shared target bucket keyed by Rust host and version. The Makefile disables Cargo incremental for this shared mode, automatically uses sccache when installed, and caps sccache at 20 GiB. Inspect it before building:

```sh
make cargo-cache-info
eval "$(python3 build/cache/cargo_cache.py env --mode shared)"
```

Shared mode is suitable for build/check/test commands. Cargo serializes writers to the shared build directory; concurrent worktrees may wait. Do not rely on its unhashed `debug/` or `release/` binaries as durable branch-specific artifacts.

Use an isolated target for a release, package assembly, a binary that will continue running, or concurrent worktree builds:

```sh
eval "$(python3 build/cache/cargo_cache.py env --mode isolated)"
```

`make platform-release` rejects the repository's default shared target. Explicit CI and caller-provided `CARGO_TARGET_DIR` values remain authoritative. For an older checkout without the helper, use a caller-owned target keyed by host/toolchain and keep different release writers isolated; do not invent or reuse a cache whose architecture, Rust version or ownership is unknown.

```sh
eval "$(python3 build/cache/cargo_cache.py env --mode shared)"
export GOCACHE="$ADX_BUILD_CACHE_ROOT/go-build"
export GOMODCACHE="$ADX_BUILD_CACHE_ROOT/go-mod"
make build JOBS=2
python3 build/ci/run.py rust --jobs 2 --output out/ci/rust-001
python3 build/ci/run.py go --jobs 2 --output out/ci/go-001
python3 build/ci/run.py agent --jobs 2 --output out/ci/agent-001
python3 build/ci/run.py sandbox-sdk --jobs 2 --output out/ci/sdk-001
python3 build/ci/run.py interop --jobs 2 --output out/ci/interop-001
```

Use a Python venv with the packages' declared dependencies. These are a menu, not a requirement to run all suites for each change. Output directories identify one run; don't overwrite failed evidence. Additional `storage`, `control-rpc` and `frontend-control` suites require Redis and, for the last one, an API executable; inspect the runner's prerequisites.

`make build` generates Go code and checks Go package compilation. To produce the standalone Go service, use the release script or its explicit `go build -o ... ./cmd/adx-sandbox-api` command.

## Unified platform release

Build natively outside the deployment nodes. Select actual existing Redis binary, target and venv paths:

```sh
eval "$(python3 build/cache/cargo_cache.py env --mode isolated)"
export ADX_REDIS_SERVER=/path/to/pinned/redis-server
export ADX_RELEASE_TARGET=x86_64-unknown-linux-gnu
export ADX_RELEASE_OUTPUT="$PWD/out/release/package-001"
make platform-release JOBS=2 PYTHON=/path/to/venv/bin/python
python3 build/release/package.py verify "$ADX_RELEASE_OUTPUT"
```

The output directory must be new; target must match the builder's native host, not an emulated promise. Retain caches from above. The package includes platform binaries, Gateway, RRT, Redis and Sandbox SDK. sandboxd is independently supplied and locked by `third_party/sandboxd/source.json`.

`make package PYTHON=/path/to/venv/bin/python` instead creates four Python distributions: Agent CLI, Agent SDK, Agent Executor and Sandbox SDK. It is not the platform process release.

## Download/build failures

Check actual compiler version, GOROOT/PATH consistency, Cargo source and cache paths first. CI image profiles can overwrite CARGO_HOME; `.buildkite/setup-cargo.sh` restores the intended ADX cache. Use the project's pinned mirrors/checksums. Package install restrictions require a venv, not system-Python overrides. Failed downloads must not cause silent version changes.

Read `.buildkite/README.md` when reproducing formal builds. Use `adx-buildkit` for CI actions rather than recreating the product pipeline here.
