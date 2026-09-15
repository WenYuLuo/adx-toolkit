---
name: adx-buildkit
description: Operate Agent DX Buildkite CI, including triggering committed revisions, monitoring independent build/image/Kubernetes E2E steps, inspecting live logs and artifact evidence, and diagnosing Cargo/image/deployment failures; the skill name is adx-buildkit but the CI service is Buildkite.
---

# ADX Buildkite

Use the selected ADX repository's `.buildkite/pipeline.yml` and `.buildkite/README.md`. This skill operates Buildkite CI. Read [pipeline and failure contracts](references/pipeline.md) before triggering, retrying or judging acceptance.

## Configure

The included `scripts/bk.py` supports trigger, status, watch, log and artifact inventory through the Buildkite REST API. It uses Python 3 standard library; no other toolkit is required.

Keep a private JSON config outside the checkout:

```json
{
  "organization": "agent-dx",
  "pipeline": "agent-dx",
  "token_file": "~/.config/adx-buildkit/token"
}
```

The token file must be readable only by its owner. Alternatively omit `token_file` and set `BUILDKITE_API_TOKEN` through an existing secret mechanism. Never pass token values on argv or commit them. The CLI defaults to `~/.config/adx-buildkit/config.json`, overridden by `--config`. API calls use normal TLS validation and environment proxy configuration.

## Read and trigger

Resolve the script relative to this skill directory, not a hard-coded user path:

```sh
python3 scripts/bk.py status 14
python3 scripts/bk.py log 14 platform-e2e --output /path/to/e2e.log --tail 60
python3 scripts/bk.py artifacts 14 --output /path/to/artifacts.json
```

Before triggering, verify user authorization, selected pipeline/account, a clean product checkout and the intended pushed branch/commit. The helper accepts a local repo plus branch and verifies remote branch HEAD matches local HEAD; a worktree's local commit alone is not enough.

```sh
python3 scripts/bk.py trigger --repo /path/to/agent-dx --branch feature/example \
  --message 'Validate committed ADX platform changes'
python3 scripts/bk.py watch BUILD_NUMBER --interval 60 --timeout 7200
```

Trigger once. On an uncertain POST outcome query recent builds using the printed request marker; don't blindly repeat submission. The helper does not retry writes automatically. A failed status read is not permission to start another build. `failing` is active; `blocked` needs attention and isn't a pass.

For long monitoring use a narrow-context worker with exact command, concurrency, success criteria and full log path; 60–180 second polling, no source edits. The parent does not separately poll. On failure return the first actionable error and evidence, fix the owning source/build issue, and retrigger only as authorized.

## Acceptance and artifacts

Require all three steps: `platform-build`, `platform-images`, `platform-e2e`. The last display name is Kubernetes E2E (Sandbox SDK); it has its own job, logs and verdict. Distinguish Buildkite job ID (API/logs) from step ID (UI links).

Judge SDK/auth/capacity/restart/stop cases plus cleanup, not merely job exit or Pod Ready. Check result JSON, JUnit, release commit/image digest and actual Pod-to-host placement. Two Pods on one host are not cross-host validation. Earlier build numbers are historical examples, not evidence for current code.

Artifact lists are paginated. Download exact requested result/placement/JUnit/summary files first, then relevant logs. Release archives and node images can be large; don't collect every artifact for routine status. Raw annotation HTML and API download URLs can contain signed credentials; use stable Buildkite page URLs in handoffs and strip query strings in saved inventories.

Use the repo's summary and tee wrappers for live compiler, deploy and per-case logs. If a command failed, preserve its original exit code through logging and summary creation. Report source failures separately from worker downloads/cache, image publication, cluster prerequisites and product assertions.
