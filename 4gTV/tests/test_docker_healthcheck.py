"""Healthcheck tests exercise path selection and the actual wget exec arguments."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HEALTHCHECK = ROOT / 'docker-healthcheck.sh'


class HealthcheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='4gtv-healthcheck-')
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.data = self.work / 'data'
        self.data.mkdir()
        self.output = self.work / 'wget.json'
        wget = self.work / 'wget'
        wget.write_text(
            '#!/usr/bin/env python3\n'
            'import json, os, pathlib, sys\n'
            'pathlib.Path(os.environ["PROBE_OUTPUT"]).write_text(json.dumps(sys.argv[1:]))\n'
            'sys.exit(int(os.environ.get("PROBE_WGET_EXIT", "0")))\n'
        )
        wget.chmod(0o755)

    def invoke(self, updates=None):
        self.assertTrue(HEALTHCHECK.is_file(), 'docker-healthcheck.sh is not implemented')
        env = dict(os.environ)
        env.update(FOURGTV_DATA_DIR=str(self.data), PORT='8080', BASE_PATH='/ignored',
                   PATH=str(self.work) + os.pathsep + env.get('PATH', ''),
                   PROBE_OUTPUT=str(self.output))
        env.update(updates or {})
        return subprocess.run(['sh', str(HEALTHCHECK)], env=env,
                              capture_output=True, text=True, timeout=5)

    def test_uses_saved_hidden_path_without_trailing_slash(self):
        (self.data / '.docker-base-path').write_text('/saved/path\n')
        result = self.invoke({'PORT': '18080', 'BASE_PATH': '/not-the-saved-path'})
        self.assertEqual(result.returncode, 0, result.stderr)
        args = json.loads(self.output.read_text())
        self.assertEqual(args[-1], 'http://127.0.0.1:18080/saved/path')
        self.assertIn('-T', args)
        self.assertIn('/dev/null', args)

    def test_empty_saved_path_probes_root(self):
        (self.data / '.docker-base-path').write_text('\n')
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.output.read_text())[-1], 'http://127.0.0.1:8080/')

    def test_missing_state_is_not_reported_healthy(self):
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists())

    def test_malformed_saved_path_fails_before_http(self):
        (self.data / '.docker-base-path').write_text('/wrong/\n')
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists())

    def test_invalid_port_fails_before_http(self):
        (self.data / '.docker-base-path').write_text('/saved\n')
        result = self.invoke({'PORT': '70000'})
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists())

    def test_http_client_failure_propagates(self):
        (self.data / '.docker-base-path').write_text('/saved\n')
        result = self.invoke({'PROBE_WGET_EXIT': '8'})
        self.assertEqual(result.returncode, 8)

    def test_saved_path_symlink_fails_before_http(self):
        target = self.work / 'elsewhere'
        target.write_text('/saved\n')
        (self.data / '.docker-base-path').symlink_to(target)
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
