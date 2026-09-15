# Three-VM procedure

## Inventory and preflight

Keep an inventory outside this toolkit, with explicit VM/SSH names, selected addresses, roles, package/config paths, evidence path and caller-approved final state. Never infer that any three running VMs are available for testing.

On each guest collect hostname, `/etc/machine-id`, `uname -m`, `/etc/os-release`, assigned addresses, free disk (including `/tmp`), memory/cgroup limits, Python version and required backend/kernel facilities. Read `build/e2e/preflight.py` for runc prerequisites. Check actual sandboxd socket, permissions and image registry access. Do not make kernel modifications on a shared host solely because a check failed.

For local Lima use current inventory first:

```sh
limactl list --json
limactl shell NODE -- uname -m
limactl shell NODE -- cat /etc/machine-id
limactl shell NODE -- ip -4 -o addr show
limactl shell NODE -- df -h / /tmp
```

Use actual names for NODE. When provisioning is explicitly requested, prefer one reviewed Linux template. Stop a source VM before cloning and regenerate cloned identities as needed. Keep LIMA_HOME short to avoid UDS path limits. On macOS, inspect current Lima networking; `user-v2` is a candidate for guest-to-guest communication, while shared/default NAT addresses may not identify unique reachable guests. Verify behavior against installed Lima version rather than editing an active VM blindly.

Lima can inject host proxies into guests. Append loopback and all selected cluster addresses to `NO_PROXY`/`no_proxy` for control/data traffic; retain external-download proxy settings where needed. Distinguish proxy failures from RPC protocol failures.

## Package and configuration

Use `build/release/package.py verify PACKAGE_DIR` from the matching source revision where available, and compare copied file hashes against the package manifest on every node. Keep the package, runtime image and installed SDK identities in evidence.

Create one deployment JSON per VM using current `build/config/examples/`. The baseline topology is:

```text
control VM: Redis (optional) → Master + Domains → Sandbox API → Edge
worker A:   Node Proxy → Node Manager → external sandboxd → Instance RRT
worker B:   Node Proxy → Node Manager → external sandboxd → Instance RRT
```

Arrows here describe launch/dependency order, not every RPC. sandboxd must already be ready before admitting instances. All deployments use one Redis URL/namespace. Redis binds a reachable protected interface and requires its configured password for non-loopback listening. Give each worker a unique `node_id`; use its reachable guest address for `advertised_address` and `proxy_address`.

Master needs both node peer identities; workers trust the selected Master/Frontend identities. API and Edge can remain co-located on the control VM with loopback HTTP upstream and public Edge TLS. Edge-to-Node mTLS is configured separately. Allow only actual Edge peers and backend target CIDRs. Populate measured, expiring capacity observations before admission.

## Run

Use an existing guest process manager to keep each foreground command alive and retain logs. Do not assume an SSH session's disconnect safely detaches a process.

```sh
/opt/adx/bin/adxctl validate --config /etc/adx/deployment.json
/opt/adx/bin/adxctl run --config /etc/adx/deployment.json
# From another guest session
/opt/adx/bin/adxctl status --config /etc/adx/deployment.json
```

Start control first, workers after Master readiness. Validate live advertised endpoints and both registrations. `state_dir` is local per supervisor; Redis `data_dir` must persist where required.

## Public validation

The existing `build/e2e/sdk_smoke.py` accepts endpoint, token file, image, CA and output arguments. It creates two instances and checks commands and binary files, but does not itself prove placement on separate workers. Read it before reuse.

```sh
python3 -u build/e2e/sdk_smoke.py \
  --endpoint edge.example:8443 --token-file /path/to/tenant-key \
  --image registry.example/team/adx-rrt@sha256:DIGEST \
  --ca /path/to/ca.pem --runtime runc --output /path/to/new-evidence
```

Replace placeholders with the inventory. To make a multi-node claim, establish placement on both workers using supported placement controls or a resource-saturation workload based on measured capacities. Keep instances alive while collecting assignment/backend identity evidence. Do not fake capacity observations to force a test outcome.

For Node Manager restart, terminate only the selected process, then prove reconciliation completed and backend identities remained unchanged. Full supervisor stop is a deleting operation. Master failure, VM power loss, cross-node checkpoint recovery and persistent-volume loss are separate test contracts; do not improvise unsupported recovery expectations.

Stop workers first when the requested test ends with cleanup, then control. Verify physical runtime deletion and published terminal state before declaring stop successful. Keep per-node component logs, SDK results, placement, package hashes and the final VM inventory. No successful ADX three-VM run is recorded merely by installing this skill.
