"""Hermetic entrypoint tests; the probe records the real exec boundary."""
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / 'docker-entrypoint.sh'
STATE_NAME = '.docker-base-path'


class EntrypointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='4gtv-entrypoint-')
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.data = self.work / 'data'
        self.output = self.work / 'exec.json'
        self.binary = self.work / 'probe-binary'
        self.binary.write_text(
            '#!/usr/bin/env python3\n'
            'import json, os, pathlib, sys\n'
            'mask = os.umask(0o077)\n'
            'pathlib.Path(os.environ["PROBE_OUTPUT"]).write_text(json.dumps({\n'
            ' "cwd": os.getcwd(), "port": os.environ.get("PORT"),\n'
            ' "base_path": os.environ.get("BASE_PATH"), "umask": mask,\n'
            ' "args": sys.argv[1:]}))\n'
        )
        self.binary.chmod(0o755)

    def invoke(self, updates=None, args=()):
        self.assertTrue(ENTRYPOINT.is_file(), 'docker-entrypoint.sh is not implemented')
        env = dict(os.environ)
        env.update(FOURGTV_DATA_DIR=str(self.data), FOURGTV_BIN=str(self.binary),
                   PORT='8080', BASE_PATH='', PROBE_OUTPUT=str(self.output))
        env.update(updates or {})
        return subprocess.run(['sh', str(ENTRYPOINT), *args], env=env,
                              capture_output=True, text=True, timeout=5)

    def successful(self, updates=None, args=()):
        result = self.invoke(updates, args)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result, json.loads(self.output.read_text())

    def test_first_start_initializes_private_path_and_execs_in_data(self):
        result, record = self.successful(args=('fixture-argument',))
        self.assertEqual(record['cwd'], str(self.data))
        self.assertEqual(record['port'], '8080')
        self.assertEqual(record['args'], ['fixture-argument'])
        self.assertEqual(record['umask'], 0o077)
        self.assertRegex(record['base_path'], r'^/[0-9a-f]{20}$')
        state = self.data / STATE_NAME
        self.assertEqual(state.read_text().strip(), record['base_path'])
        self.assertEqual(stat.S_IMODE(state.stat().st_mode), 0o600)
        self.assertNotIn(record['base_path'], result.stdout + result.stderr)

    def test_explicit_path_and_port_are_used_on_first_start(self):
        _, record = self.successful({'PORT': '18080', 'BASE_PATH': '/my/path_1-2'})
        self.assertEqual(record['port'], '18080')
        self.assertEqual(record['base_path'], '/my/path_1-2')

    def test_saved_path_survives_restart_and_changed_default(self):
        self.successful({'BASE_PATH': '/original'})
        before = (self.data / STATE_NAME).read_bytes()
        _, record = self.successful({'BASE_PATH': '/replacement', 'PORT': '65535'})
        self.assertEqual((self.data / STATE_NAME).read_bytes(), before)
        self.assertEqual(record['base_path'], '/original')
        self.assertEqual(record['port'], '65535')

    def test_saved_path_ignores_even_invalid_first_run_defaults(self):
        self.successful({'BASE_PATH': '/saved'})
        before = (self.data / STATE_NAME).read_bytes()
        for ignored_default in ('/old/', 'not-a-path', '/bad\nvalue'):
            with self.subTest(default=ignored_default):
                _, record = self.successful({'BASE_PATH': ignored_default})
                self.assertEqual(record['base_path'], '/saved')
                self.assertEqual((self.data / STATE_NAME).read_bytes(), before)

    def test_existing_app_files_are_preserved_and_permissions_tightened(self):
        self.data.mkdir()
        files = {'4gtv_config.json': b'{"keep": "exact bytes"}\n',
                 '4gtv_admin_key.txt': b'fixture-key-do-not-print\n'}
        for name, content in files.items():
            target = self.data / name
            target.write_bytes(content)
            target.chmod(0o644)
        result, _ = self.successful({'BASE_PATH': '/preserved'})
        for name, content in files.items():
            target = self.data / name
            self.assertEqual(target.read_bytes(), content)
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
        self.assertNotIn('fixture-key-do-not-print', result.stdout + result.stderr)

    def test_off_explicitly_disables_hidden_path_and_is_persistent(self):
        _, record = self.successful({'BASE_PATH': 'off'})
        self.assertEqual(record['base_path'], '')
        _, restarted = self.successful()
        self.assertEqual(restarted['base_path'], '')

    def test_invalid_ports_fail_before_creating_data_or_launching(self):
        for value in ('0', '01', '65536', '-1', 'http', '8 080', '80\n80', '9' * 40):
            with self.subTest(port=value):
                result = self.invoke({'PORT': value})
                self.assertEqual(result.returncode, 64, result.stderr)
                self.assertFalse(self.data.exists())
                self.assertFalse(self.output.exists())

    def test_invalid_paths_fail_before_creating_data_or_launching(self):
        for value in ('plain', '/', '/trailing/', '//double', '/a//b', '/a b',
                      '/a?b', '/a#b', '/a\nb', '/$(id)', '/a/../b'):
            with self.subTest(path=value):
                result = self.invoke({'BASE_PATH': value})
                self.assertEqual(result.returncode, 64, result.stderr)
                self.assertFalse(self.data.exists())
                self.assertFalse(self.output.exists())

    def test_corrupt_saved_path_is_rejected_without_evaluating_it(self):
        self.data.mkdir()
        sentinel = self.work / 'should-not-exist'
        (self.data / STATE_NAME).write_text('/valid\n$(touch ' + str(sentinel) + ')\n')
        result = self.invoke()
        self.assertEqual(result.returncode, 64, result.stderr)
        self.assertFalse(sentinel.exists())
        self.assertFalse(self.output.exists())

    def test_saved_path_symlink_is_rejected(self):
        self.data.mkdir()
        target = self.work / 'elsewhere'
        target.write_text('/elsewhere\n')
        (self.data / STATE_NAME).symlink_to(target)
        result = self.invoke()
        self.assertEqual(result.returncode, 64, result.stderr)
        self.assertFalse(self.output.exists())

    def test_secret_symlink_is_rejected_without_changing_target(self):
        self.data.mkdir()
        target = self.work / 'elsewhere'
        target.write_text('do not change\n')
        target.chmod(0o644)
        (self.data / '4gtv_admin_key.txt').symlink_to(target)
        result = self.invoke()
        self.assertEqual(result.returncode, 64, result.stderr)
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o644)
        self.assertFalse(self.output.exists())

    def test_relative_data_directory_is_rejected(self):
        result = self.invoke({'FOURGTV_DATA_DIR': 'relative-data'})
        self.assertEqual(result.returncode, 64, result.stderr)
        self.assertFalse(self.output.exists())

    def test_missing_binary_fails_before_initialization(self):
        result = self.invoke({'FOURGTV_BIN': str(self.work / 'missing')})
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.data.exists())
        self.assertFalse(self.output.exists())

    @unittest.skipIf(os.geteuid() == 0, 'permission denial requires an unprivileged test user')
    def test_unwritable_bind_directory_has_actionable_error(self):
        self.data.mkdir()
        self.data.chmod(0o500)
        try:
            result = self.invoke()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('writable', result.stderr)
            self.assertFalse(self.output.exists())
        finally:
            self.data.chmod(0o700)


if __name__ == '__main__':
    unittest.main()
