from pydantic import BaseModel


class FrontendModelOption(BaseModel):
    key: str
    label: str


class FrontendConfig(BaseModel):
    auth_enabled: bool
    key_predefined: bool
    default_model: str
    models: list[FrontendModelOption]
