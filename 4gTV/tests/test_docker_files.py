"""Packaging contracts, using Docker Compose's real parser (no YAML dependency)."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
ENV_KEYS = ('PORT', 'BASE_PATH', 'TZ', 'FOURGTV_PORT', 'FOURGTV_BIND',
            'FOURGTV_UID', 'FOURGTV_GID', 'FOURGTV_DATA_DIR', 'COMPOSE_FILE',
            'COMPOSE_PROJECT_NAME', 'COMPOSE_PROFILES')


class DockerFilesTests(unittest.TestCase):
    def text(self, name):
        path = ROOT / name
        self.assertTrue(path.is_file(), name + ' is not implemented')
        return path.read_text()

    def compose(self, override=False, updates=None):
        self.text('compose.yaml')
        if override:
            self.text('compose.cf-net.yaml')
        env = {key: value for key, value in os.environ.items() if key not in ENV_KEYS}
        env.update(updates or {})
        command = ['docker', 'compose', '--env-file', '/dev/null', '-p', 'fourgtv-contract',
                   '-f', str(ROOT / 'compose.yaml')]
        if override:
            command += ['-f', str(ROOT / 'compose.cf-net.yaml')]
        result = subprocess.run(command + ['config', '--format', 'json'], env=env,
                                text=True, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_dockerfile_pins_supplied_amd64_binary_and_rejects_other_targets(self):
        text = self.text('Dockerfile')
        digest = hashlib.sha256((ROOT / '4gtv-linux-amd64').read_bytes()).hexdigest()
        self.assertIn(digest, text)
        self.assertIn('ARG TARGETARCH', text)
        self.assertIn('amd64', text)
        self.assertIn('Unsupported platform', text)
        self.assertIn('sha256sum -c -', text)
        self.assertIn('COPY --from=binary', text)
        self.assertNotIn('4gtv-linux-arm', text)

    def test_image_runs_unprivileged_with_data_and_healthcheck(self):
        text = self.text('Dockerfile')
        self.assertIn('USER 1001:1001', text)
        self.assertIn('WORKDIR /data', text)
        self.assertIn('VOLUME ["/data"]', text)
        self.assertIn('HEALTHCHECK', text)
        self.assertIn('docker-healthcheck.sh', text)
        self.assertIn('ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]', text)
        self.assertIn('ca-certificates', text)
        for name in ('docker-entrypoint.sh', 'docker-healthcheck.sh'):
            self.assertTrue(os.access(ROOT / name, os.X_OK), name + ' must be executable')

    def test_base_compose_is_private_and_has_persistent_data(self):
        service = self.compose()['services']['4gtv']
        self.assertEqual(service['image'], '4gtv:local')
        self.assertEqual(service['platform'], 'linux/amd64')
        self.assertEqual(service['user'], '1001:1001')
        self.assertTrue(service['init'])
        self.assertTrue(service['read_only'])
        self.assertEqual(service['restart'], 'unless-stopped')
        self.assertEqual(service['cap_drop'], ['ALL'])
        self.assertIn('no-new-privileges:true', service['security_opt'])
        self.assertFalse(service.get('privileged', False))
        self.assertNotEqual(service.get('network_mode'), 'host')
        self.assertEqual(service['environment']['PORT'], '8080')
        self.assertEqual(service['environment']['BASE_PATH'], '')
        port = service['ports'][0]
        self.assertEqual(port['host_ip'], '127.0.0.1')
        self.assertEqual(port['target'], 8080)
        self.assertEqual(port['published'], '18080')
        self.assertEqual(port['protocol'], 'tcp')
        data = next(volume for volume in service['volumes'] if volume['target'] == '/data')
        self.assertEqual(data['type'], 'bind')
        self.assertEqual(data['source'], str(ROOT / 'data'))
        self.assertNotEqual(service['logging']['options'].get('max-file'), '1')

    def test_custom_host_and_container_ports_match_the_process(self):
        service = self.compose(updates={
            'PORT': '19080', 'FOURGTV_PORT': '29080', 'FOURGTV_BIND': '127.0.0.1',
            'FOURGTV_UID': '12345', 'FOURGTV_GID': '12346',
            'FOURGTV_DATA_DIR': '/tmp/fourgtv-contract-data',
        })['services']['4gtv']
        self.assertEqual(service['environment']['PORT'], '19080')
        self.assertEqual(service['ports'][0]['target'], 19080)
        self.assertEqual(service['ports'][0]['published'], '29080')
        self.assertEqual(service['user'], '12345:12346')
        self.assertEqual(service['volumes'][0]['source'], '/tmp/fourgtv-contract-data')

    def test_cf_net_keeps_default_network_and_uses_existing_external_network(self):
        model = self.compose(override=True)
        self.assertEqual(set(model['services']['4gtv']['networks']), {'default', 'cf-net'})
        self.assertEqual(model['networks']['cf-net']['name'], 'cf-net')
        self.assertTrue(model['networks']['cf-net']['external'])

    def test_build_context_is_an_explicit_allowlist_without_data_or_secrets(self):
        lines = {line.strip() for line in self.text('.dockerignore').splitlines()
                 if line.strip() and not line.startswith('#')}
        self.assertEqual(lines, {'**', '!Dockerfile', '!docker-entrypoint.sh',
                                 '!docker-healthcheck.sh', '!docker-common.sh',
                                 '!4gtv-linux-amd64'})
        ignored = self.text('.gitignore').splitlines()
        self.assertIn('data/', ignored)
        self.assertIn('.env', ignored)
        self.assertIn('__pycache__/', ignored)

    def test_basic_smoke_documentation_does_not_require_optional_cf_net(self):
        self.assertTrue('smoke_docker.py --skip-cf-net' in self.text('README.md'),
                        'basic smoke instructions must not require optional cf-net')

    def test_examples_and_documentation_describe_first_run_settings(self):
        example = self.text('.env.example')
        for setting in ('PORT=8080', 'FOURGTV_PORT=18080', 'FOURGTV_BIND=127.0.0.1',
                        'FOURGTV_UID=1001', 'FOURGTV_GID=1001', 'BASE_PATH='):
            self.assertIn(setting, example)
        readme = self.text('README.md')
        self.assertIn('## 🐳 Docker', readme)
        self.assertIn('.docker-base-path', readme)
        self.assertIn('mkdir -p data', readme)
        self.assertIn('linux/amd64', readme)
        self.assertIn('docker compose', readme)


if __name__ == '__main__':
    unittest.main()
