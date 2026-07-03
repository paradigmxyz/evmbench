import json
from typing import TypedDict

from api.util.fs import ROOT_DIR


MODEL_CATALOG_PATH = ROOT_DIR / 'model_catalog.json'


class ModelOption(TypedDict):
    key: str
    label: str
    codex_model: str


def _require_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        msg = f'{field} must be a non-empty string'
        raise ValueError(msg)
    return value.strip()


def _load_model_catalog() -> tuple[str, tuple[ModelOption, ...]]:
    raw = json.loads(MODEL_CATALOG_PATH.read_text(encoding='utf-8'))
    if not isinstance(raw, dict):
        msg = 'model catalog must be an object'
        raise TypeError(msg)

    models = raw.get('models')
    if not isinstance(models, list) or not models:
        msg = 'model catalog must contain models: [...]'
        raise ValueError(msg)

    options: list[ModelOption] = []
    seen: set[str] = set()
    for index, item in enumerate(models):
        if not isinstance(item, dict):
            msg = f'models[{index}] must be an object'
            raise TypeError(msg)
        key = _require_string(item.get('key'), f'models[{index}].key')
        if key in seen:
            msg = f'duplicate model key: {key}'
            raise ValueError(msg)
        seen.add(key)
        options.append(
            {
                'key': key,
                'label': _require_string(item.get('label'), f'models[{index}].label'),
                'codex_model': _require_string(item.get('codex_model'), f'models[{index}].codex_model'),
            }
        )

    default_key = _require_string(raw.get('default'), 'default')
    if default_key not in seen:
        msg = f'default model key is not in catalog: {default_key}'
        raise ValueError(msg)

    return default_key, tuple(options)


DEFAULT_MODEL_KEY, MODEL_OPTIONS = _load_model_catalog()
MODEL_MAP = {option['key']: option['codex_model'] for option in MODEL_OPTIONS}
ALLOWED_MODEL_KEYS = frozenset(MODEL_MAP)


def frontend_model_options() -> list[dict[str, str]]:
    return [{'key': option['key'], 'label': option['label']} for option in MODEL_OPTIONS]
