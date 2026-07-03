import json

from resultsvc.routers.v1 import _load_report


def _report_payload(*, severity: object = 'HIGH') -> dict[str, object]:
    return {
        'vulnerabilities': [
            {
                'title': 'Missing access control',
                'severity': severity,
                'summary': 'Anyone can drain funds.',
                'description': [
                    {
                        'file': 'src/Vault.sol',
                        'line_start': 10,
                        'line_end': 12,
                        'desc': 'The withdraw function is permissionless.',
                    }
                ],
                'impact': 'Loss of funds.',
                'proof_of_concept': 'Call withdraw().',
                'remediation': 'Add authorization.',
            }
        ]
    }


def test_load_report_accepts_fenced_json_and_normalizes_severity() -> None:
    report = f'```json\n{json.dumps(_report_payload())}\n```'

    loaded = _load_report(report)

    assert loaded is not None
    vulnerability = loaded['vulnerabilities'][0]
    assert vulnerability['severity'] == 'high'
    assert vulnerability['description'][0]['file'] == 'src/Vault.sol'


def test_load_report_accepts_non_string_severity_as_info() -> None:
    loaded = _load_report(json.dumps(_report_payload(severity=123)))

    assert loaded is not None
    assert loaded['vulnerabilities'][0]['severity'] == 'info'


def test_load_report_rejects_invalid_json() -> None:
    assert _load_report('not json') is None
    assert _load_report('{"vulnerabilities": [') is None


def test_load_report_rejects_invalid_model() -> None:
    payload = _report_payload()
    vulnerabilities = payload['vulnerabilities']
    assert isinstance(vulnerabilities, list)
    vulnerability = vulnerabilities[0]
    assert isinstance(vulnerability, dict)
    vulnerability.pop('impact')

    assert _load_report(json.dumps(payload)) is None
