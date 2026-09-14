#!/usr/bin/env python3
"""Build and exercise only linux/amd64; use disposable Compose resources.

Never reads the user's .env/data, changes existing services, or pushes an image.
The optional cf-net check only attaches temporary containers to an existing network.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import urllib.error
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skip-build', action='store_true')
    parser.add_argument('--skip-cf-net', action='store_true')
    parser.add_argument('--report', type=Path)
    options = parser.parse_args()
    project = 'fourgtv-smoke-' + uuid.uuid4().hex[:10]
    peer_name = project + '-peer'
    report = {'observed_at_utc': datetime.now(timezone.utc).isoformat(),
              'platform': 'linux/amd64', 'project': project, 'checks': {},
              'live_playback_tested': False, 'image_published': False}
    checks = report['checks']
    env = dict(os.environ)
    for key in ('COMPOSE_FILE', 'COMPOSE_PROJECT_NAME', 'COMPOSE_PROFILES'):
        env.pop(key, None)
    env.update(PORT='8080', BASE_PATH='', FOURGTV_BIND='127.0.0.1', FOURGTV_PORT='0',
               FOURGTV_UID=str(os.getuid()), FOURGTV_GID=str(os.getgid()), TZ='Asia/Taipei')

    def run(args, timeout=60, check=True):
        result = subprocess.run(args, cwd=ROOT, env=env, text=True,
                                capture_output=True, timeout=timeout)
        if check and result.returncode:
            # Do not dump application logs or credential-bearing configuration.
            raise RuntimeError(f'{args[0]} {args[1]} failed (exit {result.returncode}): '
                               + result.stderr.strip()[:1500])
        return result

    def inspect_container(cid):
        return json.loads(run(['docker', 'inspect', cid]).stdout)[0]

    def verify(name, condition):
        checks[name] = bool(condition)
        if not condition:
            raise AssertionError(name)

    def status(url):
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with opener.open(url, timeout=5) as response:
                return response.status
        except urllib.error.HTTPError as error:
            return error.code

    cf_id = None
    active_cf = False
    try:
        if os.getuid() == 0:
            raise RuntimeError('Run this test as an unprivileged user so bind-mount permissions are exercised')
        if not options.skip_cf_net:
            cf = run(['docker', 'network', 'inspect', 'cf-net'], check=False)
            if cf.returncode:
                raise RuntimeError('cf-net does not exist; use --skip-cf-net for the base-only test')
            cf_id = json.loads(cf.stdout)[0]['Id']
        with tempfile.TemporaryDirectory(prefix=project + '-') as temp:
            work = Path(temp)
            data = work / 'data'
            data.mkdir(mode=0o700)
            env['FOURGTV_DATA_DIR'] = str(data)
            override = work / 'smoke.json'
            override.write_text(json.dumps({
                'services': {'4gtv': {'restart': 'no', 'mem_limit': '256m',
                    'cpus': 0.5, 'healthcheck': {'interval': '2s', 'timeout': '5s',
                                                'start_period': '5s', 'retries': 10}}},
            }))

            def compose(*args, cf=False, timeout=120, check=True):
                command = ['docker', 'compose', '--env-file', '/dev/null', '-p', project,
                           '-f', str(ROOT / 'compose.yaml')]
                if cf:
                    command += ['-f', str(ROOT / 'compose.cf-net.yaml')]
                command += ['-f', str(override)]
                return run(command + list(args), timeout=timeout, check=check)

            def start(cf=False):
                compose('up', '-d', '--no-build', '--pull', 'never', '--force-recreate',
                        '--wait', '--wait-timeout', '90', cf=cf)
                cid = compose('ps', '-q', '4gtv', cf=cf).stdout.strip()
                info = inspect_container(cid)
                verify('cf_healthy' if cf else 'base_healthy',
                       info['State']['Health']['Status'] == 'healthy')
                return cid, info

            def local_origin(info):
                bindings = info['NetworkSettings']['Ports']['8080/tcp']
                verify('host_port_loopback_only', all(b['HostIp'] == '127.0.0.1' for b in bindings))
                return 'http://127.0.0.1:' + bindings[0]['HostPort']

            def files_snapshot():
                names = ('.docker-base-path', '4gtv_admin_key.txt', '4gtv_config.json',
                         'persistence-marker.txt')
                return {name: hashlib.sha256((data / name).read_bytes()).hexdigest() for name in names}

            try:
                compose('config', '--quiet')
                if not options.skip_cf_net:
                    compose('config', '--quiet', cf=True)
                if not options.skip_build:
                    compose('build', '4gtv', timeout=300)
                image = json.loads(run(['docker', 'image', 'inspect', '4gtv:local']).stdout)[0]
                report['image_id'] = image['Id']
                verify('native_amd64_image', image['Architecture'] == 'amd64' and image['Os'] == 'linux')
                cid, info = start()
                report['first_container_id'] = cid
                verify('non_root', info['Config']['User'] == f'{os.getuid()}:{os.getgid()}' and
                       run(['docker', 'exec', cid, 'id', '-u']).stdout.strip() == str(os.getuid()))
                verify('readonly_rootfs', info['HostConfig']['ReadonlyRootfs'])
                verify('all_capabilities_dropped', info['HostConfig']['CapDrop'] == ['ALL'])
                verify('init_enabled', info['HostConfig']['Init'])
                verify('no_new_privileges', 'no-new-privileges:true' in info['HostConfig']['SecurityOpt'])
                hidden = (data / '.docker-base-path').read_text().strip()
                verify('random_path_generated', hidden.startswith('/') and len(hidden) == 21)
                origin = local_origin(info)
                for suffix, expected in (('', 200), ('/player', 200), ('/admin', 200), ('/', 404)):
                    name = {'': 'homepage_http_200', '/player': 'player_http_200',
                            '/admin': 'admin_page_http_200', '/': 'trailing_slash_http_404'}[suffix]
                    verify(name, status(origin + hidden + suffix) == expected)
                verify('unprefixed_root_http_404', status(origin + '/') == 404)
                for filename in ('.docker-base-path', '4gtv_admin_key.txt', '4gtv_config.json'):
                    file = data / filename
                    verify(filename + '_private', file.is_file() and file.stat().st_size > 0
                           and stat.S_IMODE(file.stat().st_mode) == 0o600)
                (data / 'persistence-marker.txt').write_text('preserve across container recreation\n')
                before = files_snapshot()
                compose('stop', '--timeout', '5', '4gtv')
                stopped = inspect_container(cid)['State']
                report['stop_exit_code'] = stopped['ExitCode']
                verify('stops_without_sigkill', not stopped['Running'] and stopped['ExitCode'] in (0, 143))
                # Stale first-run defaults, even malformed ones, must not override saved state.
                env['BASE_PATH'] = '/ignored-after-first-start/'
                cid_after, info_after = start()
                verify('container_was_recreated', cid_after != cid)
                verify('state_key_config_and_data_preserved', files_snapshot() == before)
                verify('persisted_path_still_routes', status(local_origin(info_after) + hidden) == 200)
                if not options.skip_cf_net:
                    # Refuse an ambiguous service-name lookup, rather than contacting another 4gtv.
                    existing = json.loads(run(['docker', 'network', 'inspect', 'cf-net']).stdout)[0]
                    for other_id in existing.get('Containers', {}):
                        network = inspect_container(other_id)['NetworkSettings']['Networks']['cf-net']
                        if '4gtv' in (network.get('Aliases') or []):
                            raise RuntimeError('cf-net already has a 4gtv alias; use --skip-cf-net to avoid ambiguity')
                    active_cf = True
                    cf_cid, cf_info = start(cf=True)
                    networks = cf_info['NetworkSettings']['Networks']
                    verify('cf_and_default_networks_attached',
                           set(networks) == {project + '_default', 'cf-net'})
                    peer = run(['docker', 'run', '--rm', '--pull=never', '--name', peer_name,
                                '--network', 'cf-net', '--read-only', '--cap-drop', 'ALL',
                                '--security-opt', 'no-new-privileges', '--user', '65534:65534',
                                'alpine:3.21', 'wget', '-q', '-T', '5', '-O', '/dev/null',
                                'http://4gtv:8080' + hidden], timeout=30)
                    verify('cf_peer_reaches_service_name', peer.returncode == 0)
                    verify('cf_recreation_preserves_data', files_snapshot() == before)
                    report['cf_container_id'] = cf_cid
                else:
                    report['cf_net_skipped'] = True
            finally:
                # docker run/up can create a resource before returning a failure.
                run(['docker', 'rm', '--force', peer_name], check=False)
                down = compose('down', '--remove-orphans', '--volumes', cf=active_cf,
                               timeout=60, check=False)
                remaining = run(['docker', 'ps', '-aq', '--filter',
                                 'label=com.docker.compose.project=' + project]).stdout.strip()
                remaining_networks = run(['docker', 'network', 'ls', '-q', '--filter',
                                          'label=com.docker.compose.project=' + project]).stdout.strip()
                peer_remaining = run(['docker', 'ps', '-aq', '--filter',
                                      'name=^/' + peer_name + '$']).stdout.strip()
                verify('test_containers_removed', down.returncode == 0 and not remaining and not peer_remaining)
                verify('temporary_network_removed', not remaining_networks)
                if cf_id:
                    after = json.loads(run(['docker', 'network', 'inspect', 'cf-net']).stdout)[0]
                    verify('external_cf_net_preserved', after['Id'] == cf_id)
            verify('temporary_data_cleanup_ready', data.exists())
        verify('temporary_data_removed', not work.exists())
    except Exception as error:
        report['error'] = str(error)
    report['passed'] = not report.get('error') and bool(checks) and all(checks.values())
    report['check_count'] = len(checks)
    text = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if options.report:
        options.report.parent.mkdir(parents=True, exist_ok=True)
        options.report.write_text(text)
    print(text, end='')
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
