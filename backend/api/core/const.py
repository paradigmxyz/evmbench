# Allowed reasoning levels; keep aligned with frontend/src/data/models.json.
# Values are advisory directives for the ZCode runner (the zcode CLI has no
# native reasoning-effort flag), so keep the vocabulary identical to the
# Codex-era levels the rest of the pipeline already validates.
MODEL_REASONING_EFFORTS = {
    'zcode-glm-5.3': ('low', 'medium', 'high', 'max'),
    'zcode-glm-5.3-flash': ('low', 'medium'),
    'zcode-glm-5.3-highspeed': ('low', 'medium'),
    'zcode-glm-5.3-flashx': ('low', 'medium'),
}

ALLOWED_MODELS = set(MODEL_REASONING_EFFORTS)
