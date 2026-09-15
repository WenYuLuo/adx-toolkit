#!/usr/bin/env python3
"""Small scoped Buildkite client; credentials never appear in command arguments."""
import argparse
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

API = 'https://api.buildkite.com/v2'
TERMINAL = {'passed', 'failed', 'canceled', 'skipped', 'not_run', 'finished'}


def private_write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write(value)


def redact(value, token=''):
    if token:
        value = value.replace(token, 'REDACTED')
    value = re.sub(r'(https?://[^\s<>"?]+)\?[^\s<>"\]]+', r'\1?REDACTED', value)
    value = re.sub(r'(?i)(Bearer\s+)\S+', r'\1REDACTED', value)
    value = re.sub(r'(?i)((?:api[_-]?key|token|password|secret)\s*[=:]\s*)[^\s,;]+', r'\1REDACTED', value)
    return value


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError('API redirect refused; verify the configured organization and pipeline')


class Client:
    def __init__(self, config_path):
        cfg = json.loads(Path(config_path).expanduser().read_text())
        org, pipeline = cfg['organization'], cfg['pipeline']
        if not all(isinstance(v, str) and re.fullmatch(r'[A-Za-z0-9_-]+', v) for v in (org, pipeline)):
            raise ValueError('invalid organization or pipeline slug')
        token_path = cfg.get('token_file')
        if token_path:
            path = Path(token_path).expanduser()
            if not path.is_file() or stat.S_IMODE(path.stat().st_mode) & 0o077:
                raise ValueError('token file must be owner-only (chmod 600)')
            self.token = path.read_text().strip()
        else:
            self.token = os.environ.get('BUILDKITE_API_TOKEN', '').strip()
        if not self.token or any(c.isspace() for c in self.token):
            raise ValueError('a nonempty valid token is required')
        self.base = f'/organizations/{org}/pipelines/{pipeline}'
        self.opener = urllib.request.build_opener(NoRedirect())

    def request(self, path, data=None):
        body = None if data is None else json.dumps(data).encode()
        request = urllib.request.Request(API + self.base + path, data=body, headers={
            'Authorization': 'Bearer ' + self.token, 'Accept': 'application/json',
            'Content-Type': 'application/json', 'User-Agent': 'adx-toolkit'})
        try:
            with self.opener.open(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            raise RuntimeError(f'Buildkite API HTTP {error.code}; response body omitted') from None
        except urllib.error.URLError:
            raise RuntimeError('Buildkite API network failure; a submitted write may have an uncertain outcome') from None


def summary(build):
    return {**{k: build.get(k) for k in ('number', 'state', 'commit', 'branch', 'web_url')},
            'jobs': [{'id': j.get('id'), 'step_id': (j.get('step') or {}).get('id'),
                      'key': j.get('step_key'), 'name': j.get('name'),
                      'state': j.get('state'), 'exit_status': j.get('exit_status')}
                     for j in build.get('jobs', []) if j.get('type') == 'script']}


def select_job(build, selector):
    jobs = [j for j in build.get('jobs', []) if j.get('type') == 'script' and
            (j.get('id') == selector or j.get('step_key') == selector)]
    if len(jobs) != 1:
        raise ValueError('job selector must match exactly one script job; use status to find its ID')
    return jobs[0]


def git(repo, *args):
    result = subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True, timeout=45)
    if result.returncode:
        raise ValueError('Git verification failed; inspect the selected repository/remote')
    return result.stdout.strip()


def trigger_payload(repo, branch, remote, message, marker):
    git(repo, 'check-ref-format', '--branch', branch)
    if remote.startswith('-') or not re.fullmatch(r'[A-Za-z0-9_.-]+', remote):
        raise ValueError('use a configured remote name')
    if git(repo, 'status', '--porcelain'):
        raise ValueError('trigger requires a clean product checkout')
    if git(repo, 'branch', '--show-current') != branch:
        raise ValueError('selected branch differs from the current checkout')
    head = git(repo, 'rev-parse', 'HEAD')
    remote_lines = git(repo, 'ls-remote', '--exit-code', remote, f'refs/heads/{branch}').splitlines()
    if len(remote_lines) != 1 or remote_lines[0].split()[0] != head:
        raise ValueError('remote branch HEAD differs from local HEAD; publish/resolve the intended revision first')
    return {'commit': head, 'branch': branch, 'message': f'{message} [adx-request:{marker}]',
            'clean_checkout': True}


def print_json(value, token=''):
    print(redact(json.dumps(value, indent=2, ensure_ascii=False), token), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='~/.config/adx-buildkit/config.json')
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('status', 'watch', 'log', 'artifacts'):
        p = sub.add_parser(name)
        p.add_argument('build', type=int)
        if name == 'watch':
            p.add_argument('--interval', type=int, default=60)
            p.add_argument('--timeout', type=int, default=7200)
        if name == 'log':
            p.add_argument('job')
            p.add_argument('--tail', type=int, default=60)
            p.add_argument('--output', type=Path, required=True)
        if name == 'artifacts':
            p.add_argument('--output', type=Path, required=True)
    p = sub.add_parser('trigger')
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--branch', required=True)
    p.add_argument('--remote', default='origin')
    p.add_argument('--message', required=True)
    p = sub.add_parser('recent')
    p.add_argument('--limit', type=int, default=10)
    args = parser.parse_args()
    if getattr(args, 'build', 1) < 1:
        parser.error('build must be positive')
    if args.command == 'watch' and (not 60 <= args.interval <= 180 or args.timeout < 1):
        parser.error('watch requires interval 60..180 and positive timeout')
    if args.command == 'log' and not 1 <= args.tail <= 300:
        parser.error('tail must be 1..300')
    if args.command == 'recent' and not 1 <= args.limit <= 100:
        parser.error('limit must be 1..100')
    client = Client(args.config)
    if args.command == 'trigger':
        marker = str(uuid.uuid4())
        payload = trigger_payload(args.repo, args.branch, args.remote, args.message, marker)
        print(f'Submission marker: adx-request:{marker}', flush=True)
        print_json(summary(client.request('/builds', payload)), client.token)
    elif args.command == 'recent':
        print_json([{**summary(b), 'message': b.get('message')} for b in client.request(f'/builds?per_page={args.limit}')], client.token)
    elif args.command == 'artifacts':
        artifacts, page = [], 1
        while True:
            batch = client.request(f'/builds/{args.build}/artifacts?per_page=100&page={page}')
            artifacts.extend({k: a.get(k) for k in ('id', 'job_id', 'path', 'file_size', 'sha1sum')} for a in batch)
            if len(batch) < 100:
                break
            page += 1
        private_write(args.output, redact(json.dumps(artifacts, indent=2), client.token) + '\n')
        print_json({'count': len(artifacts), 'inventory': str(args.output)})
    elif args.command == 'log':
        job = select_job(client.request(f'/builds/{args.build}'), args.job)
        log = client.request(f'/builds/{args.build}/jobs/{job["id"]}/log')['content']
        log = redact(log, client.token)
        private_write(args.output, log)
        print('\n'.join(log.splitlines()[-args.tail:]))
        print_json({'job_id': job['id'], 'log_path': str(args.output)})
    elif args.command == 'status':
        print_json(summary(client.request(f'/builds/{args.build}')), client.token)
    else:
        started, previous = time.monotonic(), None
        while True:
            result = summary(client.request(f'/builds/{args.build}'))
            if result != previous:
                print_json(result, client.token)
                previous = result
            if result['state'] == 'blocked':
                return 3
            if result['state'] in TERMINAL:
                return 0 if result['state'] == 'passed' else 1
            remaining = args.timeout - (time.monotonic() - started)
            if remaining <= 0:
                print('Watch timed out; build may still be active', file=sys.stderr)
                return 124
            time.sleep(min(args.interval, remaining))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, RuntimeError, OSError, KeyError, subprocess.TimeoutExpired) as error:
        # Never expose auth headers, config bodies, Git output or HTTP response bodies.
        detail = str(error) if isinstance(error, (ValueError, RuntimeError)) and not isinstance(error, json.JSONDecodeError) else type(error).__name__
        print('ERROR: ' + redact(detail), file=sys.stderr)
        sys.exit(2)
