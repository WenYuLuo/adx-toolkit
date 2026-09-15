---
name: adx-standalone
description: Deploy or troubleshoot ADX on a single Linux host with adxctl and external sandboxd, and run the repository's local Docker two-node public SDK acceptance; use for standalone/process deployment, not Kubernetes or three-VM validation.
---

# ADX Standalone

First identify the requested topology: a persistent single-host process deployment or the repository's isolated local Docker two-node E2E. These have different cleanup behavior. Confirm the chosen host/context from user input or current session; do not silently substitute another cluster.

Read [deployment and acceptance commands](references/runbook.md) for the selected mode. Use the chosen product checkout's current configs and drivers as the source of truth.

## Before launch

Record repo commit, package manifest/hash, architecture, SDK version, sandboxd revision, runtime image digest, backend socket and evidence directory. Use one coherent release; obtain missing artifacts through the repository build or CI rather than mixing unrelated binaries.

sandboxd is independently hosted. The package's `runtime/rrt-runtime` must be present in the instance image at the configured command path. RRT is not a host service. Check the actual backend's kernel/network/cgroup prerequisites and sandboxd image-pull credentials before diagnosing product failures.

Node Manager reads external resource observations with a future expiry. The acceptance fixture's cgroup observations are not an implemented production automatic collector. Never advertise a configured capacity as measured without an actual collector.

## Launch and readiness

`adxctl validate`, `render`, `run/start`, `status`, `stop` are the deployed commands. `run` and `start` both remain foreground; `status` reports processes, not business readiness. For the baseline CLI there is no independent restart command.

Use shared Redis URL/namespace, reachable advertised addresses, environment-issued mTLS identities and public TLS/API Keys. Align Node Manager `proxy_socket` with the Node Proxy control directory. Internal RPC TLS and Edge-to-Node data TLS are separate settings.

Require Master discovery, node registration/reconciliation, valid capacity, complete local binding synchronization and Edge route synchronization before SDK checks. Frontend ownership-cache hits should route existing-instance actions directly to Node Manager; data flows Edge → Node Proxy → RRT.

## Acceptance and cleanup

Use the repository driver unchanged for its documented scenario set. Long runs use a narrow-context worker with exact command, concurrency, success criteria and full log path, 60–180 second monitoring, no source edits and no duplicate parent polling.

Keep per-case output and machine-readable verdict. A local two-container pass is local evidence; it is neither three VMs nor Kubernetes. Check backend inventories and released resources, not only successful HTTP DELETE.

Explicit `adxctl stop` and SIGINT/SIGTERM drain and delete local managed Instances before stopping services. A failed deletion or unpublished result leaves dependencies running for retry. Keep Master/Redis available until nodes finish. sandboxd stays outside the product supervisor. Never treat this command as a non-destructive pause or use it on unrelated deployments.

Node Manager process restart is a separate recovery test; don't substitute whole-supervisor stop, which deletes instances. Preserve original failure logs and report the final state of the caller-owned environment.
