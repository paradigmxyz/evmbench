#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any


FENCED_JSON_RE = re.compile(r'```(?:json)?\s*(.*?)```', re.DOTALL | re.IGNORECASE)


def write_output(name: str, value: str) -> None:
    output = os.environ.get('GITHUB_OUTPUT')
    if output:
        with Path(output).open('a', encoding='utf-8') as fh:
            fh.write(f'{name}={value}\n')


def extract_json(text: str) -> Any:
    match = FENCED_JSON_RE.search(text)
    if match:
        text = match.group(1)
    else:
        start = text.find('{')
        end = text.rfind('}')
        if start == -1 or end == -1 or end < start:
            raise ValueError('report does not contain a JSON object')
        text = text[start : end + 1]
    return json.loads(text)


def require_string(value: Any, field: str, *, default: str | None = None) -> str:
    if value is None and default is not None:
        return default
    if not isinstance(value, str):
        raise TypeError(f'{field} must be a string')
    return value.strip()


def normalize_description_item(value: Any, index: int, desc_index: int) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f'vulnerabilities[{index}].description[{desc_index}] must be an object')
    file_name = require_string(value.get('file'), f'vulnerabilities[{index}].description[{desc_index}].file')
    desc = require_string(value.get('desc'), f'vulnerabilities[{index}].description[{desc_index}].desc')
    line_start = value.get('line_start')
    line_end = value.get('line_end')
    if not isinstance(line_start, int) or line_start < 1:
        raise TypeError(f'vulnerabilities[{index}].description[{desc_index}].line_start must be a positive integer')
    if not isinstance(line_end, int) or line_end < line_start:
        raise TypeError(
            f'vulnerabilities[{index}].description[{desc_index}].line_end must be an integer >= line_start'
        )
    return {
        'file': file_name,
        'line_start': line_start,
        'line_end': line_end,
        'desc': desc,
    }


def normalize_report(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise TypeError('report must be a JSON object')
    vulnerabilities = data.get('vulnerabilities')
    if not isinstance(vulnerabilities, list):
        raise TypeError('report must contain vulnerabilities: []')

    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(vulnerabilities):
        if not isinstance(item, dict):
            raise TypeError(f'vulnerabilities[{index}] must be an object')
        description = item.get('description')
        if not isinstance(description, list) or not description:
            raise TypeError(f'vulnerabilities[{index}].description must be a non-empty list')

        normalized.append(
            {
                'title': require_string(item.get('title'), f'vulnerabilities[{index}].title'),
                'severity': require_string(item.get('severity'), f'vulnerabilities[{index}].severity').lower(),
                'summary': require_string(item.get('summary'), f'vulnerabilities[{index}].summary', default=''),
                'description': [
                    normalize_description_item(desc_item, index, desc_index)
                    for desc_index, desc_item in enumerate(description)
                ],
                'impact': require_string(item.get('impact'), f'vulnerabilities[{index}].impact'),
                'proof_of_concept': require_string(
                    item.get('proof_of_concept'),
                    f'vulnerabilities[{index}].proof_of_concept',
                    default='',
                ),
                'remediation': require_string(item.get('remediation'), f'vulnerabilities[{index}].remediation'),
            }
        )

    return {'vulnerabilities': normalized}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    raw = Path(args.input).read_text(encoding='utf-8')
    report = normalize_report(extract_json(raw))
    output_path = Path(args.output)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')

    findings_count = len(report['vulnerabilities'])
    write_output('report-json-file', str(output_path))
    write_output('findings-count', str(findings_count))
    write_output('has-findings', 'true' if findings_count else 'false')
    print(f'evmbench: validated {findings_count} finding(s)')


if __name__ == '__main__':
    main()
