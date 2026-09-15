# Standalone runbook

## Persistent process deployment

Use `build/config/examples/deployment.json` from the chosen revision. Prepare absolute package/state/data/socket paths, certificates, API key files, measured capacity observations and a matching RRT image. Examples require environment-specific values; validating JSON does not establish runtime readiness.

```sh
/opt/adx/bin/adxctl validate --config /etc/adx/deployment.json
/opt/adx/bin/adxctl render --config /etc/adx/deployment.json --output /tmp/adx-render-001
/opt/adx/bin/adxctl run --config /etc/adx/deployment.json
# Another shell
/opt/adx/bin/adxctl status --config /etc/adx/deployment.json
```

The render directory must not exist. Generated config/socket permissions are private to the service user. Logs are `state_dir/logs/<service-id>.log`; supervisor messages go to its parent terminal/service log. Do not dump configuration or secrets into evidence.

Single-host services can include Redis, Master with embedded Domain, Node Proxy, Node Manager, Sandbox API and Edge. Redis may instead be external. Current packaging supports separate Node Proxy/Manager processes; verify before claiming embedded assembly exists.

Edge's current control upstream uses HTTP. For the baseline runtime place API on literal loopback with `loopback_http: true`; set Edge's control address to the same listener. If an older sample contains `CONTROL_PLANE_ROUTES="[]"`, it is not valid route syntax: inspect `parse_static_routes` and use the required `prefix:/api/sandbox,prefix:/api/agent` form. Do not wire plaintext HTTP to the example API's HTTPS listener.

Install the package's SDK wheel in a venv. Use the SDK's ConnectionConfig, deployment CA and tenant key; run create, command with stdout/stderr/exit assertions, binary file round-trip, then explicit `kill()` and client `close()`. Read the current `build/e2e/sdk_smoke.py` for the exact public SDK assertions. This helper creates two instances, so capacity must support both.

## Isolated local Docker E2E

These commands build/run a new dedicated environment. Use a matching native Linux Docker host, not an arbitrary existing business deployment. Build/package first outside the runtime nodes.

```sh
python3 build/e2e/build_backend.py \
  --redis-cli /path/to/pinned/redis-cli --jobs 2 --output out/e2e/backend-001
python3 build/e2e/prepare.py \
  --package out/release/package-001 --backend out/e2e/backend-001 \
  --runtime-base registry.example/team/adx-tools@sha256:DIGEST \
  --rrt-base registry.example/team/rrt-base@sha256:DIGEST \
  --output out/e2e/bundle-001
python3 -u build/e2e/run.py \
  --bundle out/e2e/bundle-001 --output out/e2e/run-001
```

Replace every image example with an actual verified digest. The Docker daemon must see the same bind-mount paths as the driver. Follow `build/e2e/README.md` and `build/images/Dockerfile.e2e-runtime` for prerequisites. The backend builder pins sandboxd and helpers from repository inputs, not upstream HEAD.

The five baseline scenarios cover SDK create/query/command/file/delete, invalid/cross-tenant credentials, resource exhaustion/release, Node Manager process restart and supervisor stop with physical cleanup. Save result JSON, JUnit, component logs and identity records. The baseline uses runc, no idle recycling and no writable-layer quota; it does not validate checkpoints, XPU or automatic recovery.

## Diagnose by layer

- sandboxd startup fails: check EROFS, bridge netfilter, backend/network permissions and image pull separately from ADX.
- Node never admits: check authoritative reconciliation and capacity expiry, not only PID.
- RRT readiness fails: verify image binary, injected identity, IP/port and HTTP service.
- Edge fails after node restart: inspect full binding sync, generation and route publication.
- stop fails: inspect Node Drain, physical deletion and Master/Redis commit; recover dependencies and retry within the same deployment.

End with status, first error (if any), scenario verdict, evidence paths and whether the caller's deployment was preserved or stopped.
