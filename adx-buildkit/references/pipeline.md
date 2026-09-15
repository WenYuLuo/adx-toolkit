# ADX Buildkite pipeline

## Source and execution

Before action, read the selected revision's `.buildkite/{pipeline.yml,README.md,build-e2e.sh,package-e2e.sh,run-e2e.sh}`. The historical baseline is listed in the toolkit's sources.json; re-read current organization/pipeline metadata and actual image/toolchain pins.

| Step | Required outcome |
|---|---|
| platform-build | Current clean commit; Rust/Go/SDK build; verified unified release and external backend identity |
| platform-images | Exact archive/checksum handoff; immutable Node/RRT registry references tied to bundle identity |
| platform-e2e | Independent K8s deployment, backend/platform readiness, five SDK scenario groups, diagnostics and scoped cleanup |

Reuse existing CI worker images through the product configuration. The builder has persistent Cargo registry/git/target caches, configured sparse source, Go caches and optional sccache. Image profile initialization can override CARGO_HOME: `.buildkite/setup-cargo.sh` restores it through ADX_CARGO_HOME. Check actual exported cache paths and Rust version in bootstrap logs.

## External backend

`third_party/sandboxd/source.json` pins upstream revision and vendored protocol hashes. `build/e2e/verify_backend.py` verifies revision, native target, required files and SHA256. `ADX_BACKEND_ARTIFACT_BUILD` can select a previously built external backend by Buildkite build UUID; it does not select old ADX product binaries. Read the actual backend manifest before claiming the version used in a run.

Native builder and runtime architecture must match. Go's GOROOT must match PATH; use the repo's pinned bootstrap downloads. Keep Python packages in a venv. Redis packaging checks its pin and ABI constraints. Retry network reads within limits; don't upgrade dependencies to work around transient fetch failures.

## Kubernetes environment

Use the deployment job's explicit target kubeconfig and context. The worker needs a pullable deployer image and registry access; normal CI status/log reads need neither cluster kubeconfig nor SWR credentials. Do not copy these credentials into the skill repo.

The E2E creates a unique namespace and two privileged node Pods using the release. node1 runs control services plus one worker; node2 runs the second worker. sandboxd is separately started by the fixture. The default test uses private Pod networking and ephemeral test state; it does not prove persistence after Pod deletion.

The selected host pool must already have EROFS and bridge netfilter with `bridge-nf-call-iptables=1`. `ADX_E2E_NODE_NAMES` or repeatable driver `--node-name` can restrict eligibility. Use explicit environment configuration, not a historical hard-coded host address. Preferred anti-affinity does not ensure two physical hosts.

Live E2E output must show deployment commands, readiness, case RUN/PASS/FAIL with duration and cleanup. If the UI doesn't show an expected step, inspect actual job/step labels and IDs instead of claiming it is hidden in another job.

## Failure handling

1. Read the failing step, first relevant error and source/artifact identity.
2. Classify build dependencies/cache, image handoff/registry, target-host prerequisites, credentials/topology, or product scenario failure.
3. Preserve result/cleanup evidence. Fix in the owning source or task-specific environment without changing unrelated cluster settings.
4. Revalidate the relevant layer and trigger one new committed build if authorized; never retrigger solely because monitoring disconnected.

Raw process argv/env, Secret manifests and signed S3 URLs can leak credentials. The helper returns selected build/job fields and sanitized inventories rather than whole API objects. For raw logs, review the stored bounded/redacted extract; automated redaction isn't proof that every application-generated secret was removed.

## Final verdict

Check `result.json`, `case-results.json`, `junit.xml`, `placement.json` and cumulative `summaries/e2e.json`. Five required scenario groups are sdk, auth, capacity, restart and stop. Missing scenarios, nonempty cleanup_errors or deployment errors prevent a pass. Report exact commit, build/job URL, case result, placement and untested features.

Build #14 historically passed these gates on two Pods sharing one physical host. Do not present that record as current-HEAD or three-VM acceptance.
