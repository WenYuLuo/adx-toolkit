import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


bk = module('bk', 'adx-buildkit/scripts/bk.py')
installer = module('install', 'scripts/install.py')
validator = module('validate', 'scripts/validate.py')


class Helpers(unittest.TestCase):
    def test_skill_links(self):
        self.assertEqual(validator.validate(), [])

    def test_install_is_idempotent_and_independent(self):
        with tempfile.TemporaryDirectory() as directory:
            installer.install(directory, ['adx-dev'])
            installer.install(directory, ['adx-dev'])
            dest = Path(directory) / 'adx-dev'
            self.assertTrue(dest.is_symlink())
            self.assertTrue((dest / 'references/build.md').is_file())
            self.assertFalse((Path(directory) / 'adx-3vm').exists())

    def test_install_preflights_all_conflicts(self):
        with tempfile.TemporaryDirectory() as directory:
            conflict = Path(directory) / 'adx-buildkit'
            conflict.mkdir()
            (conflict / 'keep').write_text('user-owned')
            with self.assertRaises(ValueError):
                installer.install(directory, ['adx-dev', 'adx-buildkit'])
            self.assertFalse((Path(directory) / 'adx-dev').exists())
            self.assertEqual((conflict / 'keep').read_text(), 'user-owned')

    def test_install_rejects_unexpected_name(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                installer.install(directory, ['../outside'])

    def test_private_output_cannot_replace_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'log'
            bk.private_write(path, 'first')
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                bk.private_write(path, 'replacement')
            self.assertEqual(path.read_text(), 'first')

    def test_redaction(self):
        result = bk.redact('token=foo password=bar Bearer abc https://s3.example/log?X-Amz-Credential=xyz exact-secret', 'exact-secret')
        for forbidden in ('foo', 'bar', 'abc', 'xyz', 'exact-secret'):
            self.assertNotIn(forbidden, result)
        self.assertIn('https://s3.example/log?REDACTED', result)

    def test_summary_never_returns_environment(self):
        raw = {'state': 'failing', 'env': {'PASSWORD': 'hidden'}, 'jobs': [
            {'type': 'script', 'id': 'job', 'step_key': 'platform-e2e', 'step': {'id': 'step'}, 'env': {'TOKEN': 'hidden'}},
            {'type': 'waiter', 'env': {'TOKEN': 'hidden'}}]}
        result = bk.summary(raw)
        self.assertNotIn('hidden', str(result))
        self.assertEqual(result['jobs'][0]['id'], 'job')
        self.assertEqual(result['jobs'][0]['step_id'], 'step')
        self.assertNotIn('failing', bk.TERMINAL)

    def test_retried_jobs_require_exact_job_id(self):
        raw = {'jobs': [{'type': 'script', 'id': n, 'step_key': 'platform-e2e', 'step': {'id': 'step'}} for n in ('one', 'two')]}
        with self.assertRaises(ValueError):
            bk.select_job(raw, 'platform-e2e')
        self.assertEqual(bk.select_job(raw, 'two')['id'], 'two')

    def test_redirect_does_not_forward_authorization(self):
        request = urllib.request.Request('https://api.buildkite.com/v2', headers={'Authorization': 'Bearer secret'})
        with self.assertRaises(RuntimeError):
            bk.NoRedirect().redirect_request(request, None, 302, '', {}, 'https://other.example/')

    def test_insecure_token_file_rejected(self):
        import json
        with tempfile.TemporaryDirectory() as directory:
            token, config = Path(directory) / 'token', Path(directory) / 'config.json'
            token.write_text('secret')
            token.chmod(0o644)
            config.write_text(json.dumps({'organization': 'agent-dx', 'pipeline': 'agent-dx', 'token_file': str(token)}))
            with self.assertRaises(ValueError):
                bk.Client(config)
            token.chmod(0o600)
            self.assertEqual(bk.Client(config).token, 'secret')

    def test_trigger_requires_clean_published_branch(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            source, remote = directory / 'source', directory / 'remote.git'
            def run(*args):
                return subprocess.run(['git', *map(str, args)], check=True, capture_output=True, text=True).stdout.strip()
            run('init', '--bare', remote)
            run('init', '-b', 'main', source)
            run('-C', source, 'config', 'user.name', 'Fixture')
            run('-C', source, 'config', 'user.email', 'fixture@example.invalid')
            (source / 'file').write_text('one')
            run('-C', source, 'add', 'file')
            run('-C', source, 'commit', '-m', 'init')
            run('-C', source, 'remote', 'add', 'origin', remote)
            run('-C', source, 'push', 'origin', 'main')
            payload = bk.trigger_payload(source, 'main', 'origin', 'test', 'marker')
            self.assertEqual(payload['commit'], run('-C', source, 'rev-parse', 'HEAD'))
            self.assertIn('adx-request:marker', payload['message'])
            (source / 'file').write_text('two')
            with self.assertRaises(ValueError):
                bk.trigger_payload(source, 'main', 'origin', 'test', 'marker')
            run('-C', source, 'commit', '-am', 'next')
            with self.assertRaises(ValueError):
                bk.trigger_payload(source, 'main', 'origin', 'test', 'marker')

    def test_artifact_pagination_omits_signed_urls(self):
        import json
        class Fake:
            token = 'a-secret'
            calls = []
            def __init__(self, config): pass
            def request(self, path):
                self.calls.append(path)
                count = 100 if path.endswith('&page=1') else 1
                return [{'id': str(n), 'path': f'logs/{n}', 'download_url': 'https://s3.example/?secret=private'} for n in range(count)]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'artifacts.json'
            with patch.object(bk, 'Client', Fake), patch('sys.argv', ['bk.py', 'artifacts', '14', '--output', str(output)]), patch('builtins.print'):
                self.assertEqual(bk.main(), 0)
            self.assertEqual(len(json.loads(output.read_text())), 101)
            self.assertNotIn('private', output.read_text())
            self.assertEqual(len(Fake.calls), 2)


if __name__ == '__main__':
    unittest.main()
