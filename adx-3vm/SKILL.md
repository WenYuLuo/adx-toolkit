---
name: adx-3vm
description: Prepare, deploy, validate or troubleshoot ADX process deployment on three explicitly selected Linux VMs, including explicitly requested Lima KVM runtime preflight; use for one control node and two workers, cross-node routing and fault evidence, not cloud provisioning or Kubernetes Pods.
---

# ADX Three VMs

For full three-VM deployment, use three caller-selected VMs: one control node and two workers unless the user supplies a different role mapping. Record inventory, connection method and artifact identity before changing any node. Read [the three-VM procedure](references/runbook.md) and the selected product's current deployment contract.

This skill supplies an operational contract, not an existing automated ADX three-VM harness. The baseline product contains local Docker and Kubernetes acceptance drivers; neither is a drop-in SSH/VM runner. If the request needs automation, build a scoped adapter around the public SDK assertions and existing `adxctl`, and verify it without changing those assertions to pass.

For an explicitly requested single Lima VM or Firecracker/KVM environment preflight, read [Lima ARM64 KVM validation](references/lima-kvm.md). Reuse the installed Lima executable and recorded custom `LIMA_HOME`; absence from PATH does not mean Lima is missing. Provision only the requested topology.

## Runtime/build separation

Build on a dedicated native Linux builder or CI and distribute one verified package, matching SDK and runtime images. Don't compile on a runtime VM by default. Verify architecture, OS/shared-library compatibility, hashes and tool versions on all three nodes before launch. A VM on an Apple Silicon host still needs an architecture-compatible sandboxd and runtime artifact set.

## Topology and readiness

Require distinct machine IDs, hostnames and selected addresses. Check all directed inter-node paths plus the actual RPC, Redis and data endpoints required by the chosen role map. Three VMs on one host demonstrate guest-network distribution, not physical-host fault isolation.

Control node: Master with embedded Domains, Sandbox API, Edge and optional managed Redis. Workers: Node Manager, Node Proxy, independently hosted sandboxd, measured capacity producer and RRT-capable instance images. Use unique node IDs and automatic Master-assigned domain membership.

Shared Redis/namespace, TLS peers/SANs, Edge-to-Node mTLS, allowed CIDRs and advertised worker addresses must reflect this topology. Default loopback-only Redis or ACL examples won't work across VMs. Keep runtime protected-control-network boundaries in the deployment, not user-overridable workload policy.

Master starts first; wait for discovery and persistence readiness, then start workers. Require both node registrations and reconciliations, valid capacity, binding readiness and Edge route synchronization. `adxctl status` and VM ping alone are insufficient.

## Validation

Use public Sandbox SDK assertions from the selected repo. Force or demonstrate placement on both expected workers, then verify per-instance backend ownership and command/file results. Record actual placement, not just the number of ready nodes. Add fault tests only as requested and only for implemented contracts.

Long tests/monitoring go to a narrow-context worker: exact repo/commands, concurrency, success criteria and log path, no source edits, 60–180 second polling. Parent waits for events and does not duplicate polling.

Explicit stop deletes the local node's Instances before terminating services. Stop workers before the control node so result publication can complete. Preserve failures before cleanup. Stop or retain the VMs according to the user's requested final state; don't delete reusable VMs as routine cleanup.

## Report

Return release identity, three-VM identity/placement, required scenario outcomes, per-node logs, cleanup and final VM state. Distinguish a healthy cluster with failing product assertions from inaccessible VMs, wrong binaries or incomplete setup. Do not claim an automatic failover or checkpoint guarantee from successful restart of Node Manager alone.
