from pydantic import BaseModel


class FrontendConfig(BaseModel):
    auth_enabled: bool
    key_predefined: bool
