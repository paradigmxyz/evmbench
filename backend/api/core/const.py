# Allowed reasoning levels (non-reasoning mode is disabled); keep aligned with frontend/src/data/models.json.
MODEL_REASONING_EFFORTS = {
    'codex-gpt-5.2': ('low', 'medium', 'high', 'xhigh'),
    'codex-gpt-5.3-codex': ('low', 'medium', 'high', 'xhigh'),
    'codex-gpt-5.4': ('low', 'medium', 'high', 'xhigh'),
    'codex-gpt-5.5': ('low', 'medium', 'high', 'xhigh'),
    'codex-gpt-5.6-sol': ('low', 'medium', 'high', 'xhigh', 'max'),
    'codex-gpt-5.6-terra': ('low', 'medium', 'high', 'xhigh', 'max'),
    'codex-gpt-5.6-luna': ('low', 'medium', 'high', 'xhigh', 'max'),
    'codex-gpt-6-astra': ('low', 'medium', 'high', 'xhigh', 'max'),
}

ALLOWED_MODELS = set(MODEL_REASONING_EFFORTS)
