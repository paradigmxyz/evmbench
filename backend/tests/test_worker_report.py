# ruff: noqa: PT009, SLF001
import json
import unittest

from test_shared_keys import worker


class WorkerReportTests(unittest.TestCase):
    def test_fenced_report_parses(self) -> None:
        report = {'vulnerabilities': [{'title': 'Reentrancy in withdraw', 'severity': 'high'}]}
        audit_md = f'```json\n{json.dumps(report, indent=2)}\n```\n'

        self.assertEqual(worker._extract_json_payload(audit_md), report)

    def test_code_fence_inside_json_string_does_not_truncate_report(self) -> None:
        report = {
            'vulnerabilities': [
                {
                    'title': 'Reentrancy in withdraw',
                    'severity': 'high',
                    'proof_of_concept': '```solidity\nvault.withdraw(1 ether);\n```',
                },
            ],
        }
        audit_md = f'```json\n{json.dumps(report, indent=2)}\n```\n'

        self.assertEqual(worker._extract_json_payload(audit_md), report)


if __name__ == '__main__':
    unittest.main()
