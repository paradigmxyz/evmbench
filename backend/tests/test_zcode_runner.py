# ruff: noqa: PT009, PLC0415, SLF001
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER_DIR = REPO_ROOT / 'backend' / 'worker_runner'
FAKE_ZCODE = f"""#!{sys.executable}
import json, os, sys
from pathlib import Path
argv = sys.argv[1:]
Path(os.environ['LOGS_DIR'], 'args.json').write_text(json.dumps({{
    'argv': argv,
    'home': os.environ.get('HOME'),
    'provider_config': os.environ.get('ZCODE_PERSONAL_PROVIDER_CONFIG_FILE'),
    'prompt': argv[argv.index('-p') + 1] if '-p' in argv else None,
}}))
Path(os.environ['SUBMISSION_DIR'], 'audit.md').write_text('```json\\n{{"vulnerabilities": []}}\\n```')
"""

FAKE_PROVIDER_CONFIG = {
    'schemaVersion': 1,
    'config': {
        'providerConfigRules': {
            'providerRules': [
                {
                    'providerId': 'account:bigmodel-individual-coding-plan',
                    'config': {
                        'modelOrder': ['GLM-5.3', 'GLM-5.3-Flash', 'GLM-5.3-HighSpeed', 'GLM-5.3-FlashX'],
                    },
                }
            ]
        },
        'defaultModelSelection': {
            'providerId': 'account:bigmodel-individual-coding-plan',
            'modelId': 'GLM-5.3',
        },
    },
}


class ZcodeRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.root = root

        bin_dir = root / 'bin'
        bin_dir.mkdir()
        zcode = bin_dir / 'zcode'
        zcode.write_text(FAKE_ZCODE)
        zcode.chmod(0o755)

        home = root / 'home'
        (home / '.zcode' / 'v2').mkdir(parents=True)
        (home / '.zcode' / 'v2' / 'provider_config.json').write_text(json.dumps(FAKE_PROVIDER_CONFIG))

        self.agent_dir = root / 'agent'
        self.logs_dir = root / 'logs'
        self.agent_dir.mkdir()
        self.logs_dir.mkdir()

        self.base_env = {
            'PATH': f'{bin_dir}:/usr/bin:/bin',
            'AGENT_DIR': str(self.agent_dir),
            'SUBMISSION_DIR': str(self.agent_dir / 'submission'),
            'LOGS_DIR': str(self.logs_dir),
            'EVM_BENCH_DETECT_MD': str(RUNNER_DIR / 'detect.md'),
            'EVM_BENCH_ZCODE_HOME': str(home),
            'HOME': str(self.agent_dir),  # the worker overrides HOME before the runner
        }

    def _run(self, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        env = {**self.base_env, **(extra_env or {})}
        return subprocess.run(  # noqa: S603
            [str(RUNNER_DIR / 'run_zcode_detect.sh')],
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )

    def test_invokes_zcode_headless_with_model_pinned(self) -> None:
        result = self._run({'AGENT_MODEL': 'GLM-5.3-Flash', 'CODEX_REASONING_EFFORT': 'high'})
        self.assertEqual(result.returncode, 0, result.stderr)

        recorded = json.loads((self.logs_dir / 'args.json').read_text())
        argv = recorded['argv']
        self.assertEqual(argv[argv.index('--mode') + 1], 'yolo')
        self.assertEqual(argv[argv.index('--cwd') + 1], str(self.agent_dir))
        self.assertIn('AGENTS.md', recorded['prompt'])
        self.assertIn('thorough', recorded['prompt'])
        # Real home restored so the CLI can find its credentials.
        self.assertEqual(recorded['home'], self.base_env['EVM_BENCH_ZCODE_HOME'])

        # Model pinned through a per-job provider config copy.
        pinned_path = Path(recorded['provider_config'])
        self.assertEqual(pinned_path, self.agent_dir / '.zcode_provider_config.json')
        pinned = json.loads(pinned_path.read_text())
        selection = pinned['config']['defaultModelSelection']
        self.assertEqual(selection['modelId'], 'GLM-5.3-Flash')
        order = pinned['config']['providerConfigRules']['providerRules'][0]['config']['modelOrder']
        self.assertEqual(order[0], 'GLM-5.3-Flash')
        # The user's original config must stay untouched.
        source_config = Path(self.base_env['EVM_BENCH_ZCODE_HOME']) / '.zcode' / 'v2' / 'provider_config.json'
        original = json.loads(source_config.read_text())
        self.assertEqual(original['config']['defaultModelSelection']['modelId'], 'GLM-5.3')

        self.assertTrue((self.agent_dir / 'AGENTS.md').exists())
        self.assertTrue((self.agent_dir / 'submission' / 'audit.md').exists())

    def test_defaults_to_medium_effort_and_ambient_model(self) -> None:
        result = self._run()
        self.assertEqual(result.returncode, 0, result.stderr)
        recorded = json.loads((self.logs_dir / 'args.json').read_text())
        self.assertIn('Balance thoroughness', recorded['prompt'])
        pinned = json.loads(Path(recorded['provider_config']).read_text())
        self.assertEqual(pinned['config']['defaultModelSelection']['modelId'], 'GLM-5.3')

    def test_max_effort_directive(self) -> None:
        result = self._run({'CODEX_REASONING_EFFORT': 'max'})
        self.assertEqual(result.returncode, 0, result.stderr)
        recorded = json.loads((self.logs_dir / 'args.json').read_text())
        self.assertIn('Spare no effort', recorded['prompt'])

    def test_missing_audit_output_fails(self) -> None:
        zcode = self.root / 'bin' / 'zcode'
        zcode.write_text(f'#!{sys.executable}\nimport sys\nsys.exit(0)\n')
        result = self._run()
        self.assertEqual(result.returncode, 2)
        self.assertIn('missing expected output', result.stderr)

    def test_proxy_mode_rejected(self) -> None:
        result = self._run({'OAI_PROXY_BASE_URL': 'http://proxy.invalid'})
        self.assertEqual(result.returncode, 2)
        self.assertIn('proxy', result.stderr)

    def test_invalid_effort_rejected(self) -> None:
        result = self._run({'CODEX_REASONING_EFFORT': 'ultra'})
        self.assertEqual(result.returncode, 2)
        self.assertIn('CODEX_REASONING_EFFORT', result.stderr)


class ZcodeWatchdogTests(unittest.TestCase):
    def test_timeout_kills_process_group(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / 'out.log'
            proc = subprocess.run(  # noqa: S603
                [
                    sys.executable,
                    str(RUNNER_DIR / 'zcode_watchdog.py'),
                    '1',
                    str(log),
                    '--',
                    sys.executable,
                    '-c',
                    'import time,os,sys\nprint(os.getpid(),flush=True)\ntime.sleep(300)',
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(proc.returncode, 124)
            self.assertIn('timeout after', log.read_text())

    def test_child_exit_code_forwarded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / 'out.log'
            proc = subprocess.run(  # noqa: S603
                [
                    sys.executable,
                    str(RUNNER_DIR / 'zcode_watchdog.py'),
                    '10',
                    str(log),
                    '--',
                    sys.executable,
                    '-c',
                    'import sys;sys.exit(7)',
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(proc.returncode, 7)


if __name__ == '__main__':
    unittest.main()


class ReportExtractionTests(unittest.TestCase):
    """The worker must accept reports whose PoC strings embed ``` fences."""

    @classmethod
    def setUpClass(cls) -> None:
        from importlib.util import module_from_spec, spec_from_file_location

        spec = spec_from_file_location('worker_init', REPO_ROOT / 'backend/docker/worker/init.py')
        cls.worker = module_from_spec(spec)
        spec.loader.exec_module(cls.worker)

    def _audit_with_embedded_fence(self) -> str:
        poc = 'step 1:\n```\ncontract Attack { function pwn() external {} }\n```\nstep 2: drain'
        payload = {
            'vulnerabilities': [
                {
                    'title': 'Reentrancy in withdrawAll',
                    'severity': 'high',
                    'summary': 's',
                    'description': [{'file': 'src/V.sol', 'line_start': 1, 'line_end': 2, 'desc': 'd'}],
                    'impact': 'i',
                    'proof_of_concept': poc,
                    'remediation': 'r',
                }
            ]
        }
        return f'```json\n{json.dumps(payload, indent=2)}\n```\n'

    def test_embedded_fences_do_not_truncate_json(self) -> None:
        audit_md = self._audit_with_embedded_fence()
        payload = self.worker._extract_json_payload(audit_md)
        vulns = payload['vulnerabilities']
        self.assertEqual(len(vulns), 1)
        self.assertIn('```', vulns[0]['proof_of_concept'])

    def test_plain_fenced_report_still_parses(self) -> None:
        payload = self.worker._extract_json_payload('```json\n{"vulnerabilities": []}\n```\n')
        self.assertEqual(payload, {'vulnerabilities': []})


if __name__ == '__main__':
    unittest.main()
