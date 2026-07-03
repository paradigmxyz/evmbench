#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


def write_output(name: str, value: str) -> None:
    output = os.environ.get('GITHUB_OUTPUT')
    if output:
        with Path(output).open('a', encoding='utf-8') as fh:
            fh.write(f'{name}={value}\n')


def read_files(files_file: str | None) -> list[str]:
    if not files_file:
        return []
    path = Path(files_file)
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def render_location(item: dict[str, Any]) -> str:
    file_name = item['file']
    line_start = item['line_start']
    line_end = item['line_end']
    if line_start == line_end:
        return f'`{file_name}:{line_start}`'
    return f'`{file_name}:{line_start}-{line_end}`'


def render(report: dict[str, Any], files: list[str]) -> str:
    vulnerabilities = report.get('vulnerabilities') or []
    lines = ['## evmbench audit', '']

    if files:
        lines.append(f'Reviewed {len(files)} Solidity file(s) selected for this run.')
        lines.append('')

    if not vulnerabilities:
        lines.append('No high-confidence loss-of-funds findings were identified.')
        lines.append('')
        return '\n'.join(lines)

    lines.append(f'Found {len(vulnerabilities)} high-confidence loss-of-funds finding(s).')
    lines.append('')
    lines.append('### Findings')
    lines.append('')

    for index, vuln in enumerate(vulnerabilities, start=1):
        lines.append(f"#### {index}. {vuln['title']}")
        lines.append('')
        lines.append(f"- Severity: {vuln['severity']}")
        if vuln.get('summary'):
            lines.append(f"- Summary: {vuln['summary']}")
        lines.append(f"- Impact: {vuln['impact']}")
        if vuln.get('proof_of_concept'):
            lines.append(f"- Proof of concept: {vuln['proof_of_concept']}")
        lines.append(f"- Suggested fix: {vuln['remediation']}")
        lines.append('')
        lines.append('Affected code:')
        for desc in vuln['description']:
            lines.append(f"- {render_location(desc)}: {desc['desc']}")
        lines.append('')

    return '\n'.join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--files-file')
    args = parser.parse_args()

    report = json.loads(Path(args.input).read_text(encoding='utf-8'))
    files = read_files(args.files_file)
    output_path = Path(args.output)
    output_path.write_text(render(report, files), encoding='utf-8')
    write_output('comment-file', str(output_path))
    print(f'evmbench: wrote comment to {output_path}')


if __name__ == '__main__':
    main()
