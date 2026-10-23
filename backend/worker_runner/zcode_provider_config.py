#!/usr/bin/env python3
"""Pin the ZCode default model in a per-job copy of the personal provider config.

The zcode CLI has no `--model` flag: headless prompts resolve the model from
the personal provider config (modelOrder of the selected provider plus
defaultModelSelection). To run each job on a requested model without touching
the user's global config, we copy it, move the target model to the front of
every matching modelOrder, and set defaultModelSelection. The runner exports
ZCODE_PERSONAL_PROVIDER_CONFIG_FILE pointing at the copy (the bundled wrapper
honors a pre-set value).

Usage: zcode_provider_config.py SOURCE DEST MODEL_ID
Exit codes: 0 pinned, 2 usage error, 3 source missing/unusable (runner falls
back to the ambient default model).
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
import tempfile
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('dest', type=Path)
    parser.add_argument('model_id')
    return parser.parse_args()


def pin_provider_rules(config: dict, model_id: str, provider_id: str | None) -> None:
    rules = config.get('providerConfigRules') or {}
    for rule in rules.get('providerRules') or []:
        if not isinstance(rule, dict):
            continue
        rule_config = rule.get('config')
        if not isinstance(rule_config, dict):
            continue
        order = rule_config.get('modelOrder')
        if not isinstance(order, list):
            continue
        # Only touch the provider the selection points at; if unknown, patch
        # any rule that already lists the model (never invent entries).
        if provider_id is not None:
            if rule.get('providerId') != provider_id:
                continue
        elif model_id not in order:
            continue
        rule_config['modelOrder'] = [model_id, *[m for m in order if m != model_id]]


def _warn(message: str) -> None:
    sys.stderr.write(f'{message}\n')


def pin_model(source: Path, dest: Path, model_id: str) -> int:
    try:
        data = json.loads(source.read_text(encoding='utf-8'))
    except (OSError, ValueError) as err:
        _warn(f'provider config unreadable ({source}): {err}')
        return 3
    if not isinstance(data, dict):
        _warn(f'provider config is not an object: {source}')
        return 3

    config = data.get('config')
    if not isinstance(config, dict):
        config = {}
        data['config'] = config

    selection = config.get('defaultModelSelection')
    provider_id = selection.get('providerId') if isinstance(selection, dict) else None
    config['defaultModelSelection'] = {
        **(selection if isinstance(selection, dict) else {}),
        'modelId': model_id,
    }
    pin_provider_rules(config, model_id, provider_id)

    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=dest.parent, prefix='.provider-', suffix='.json')
    os.close(fd)
    tmp = Path(tmp_path)
    try:
        with tmp.open('w', encoding='utf-8') as fh:
            json.dump(data, fh, indent=2)
        tmp.replace(dest)
    except OSError as err:
        _warn(f'failed to write {dest}: {err}')
        with contextlib.suppress(OSError):
            tmp.unlink(missing_ok=True)
        return 3
    return 0


if __name__ == '__main__':
    sys.exit(pin_model(**vars(parse_args())))
