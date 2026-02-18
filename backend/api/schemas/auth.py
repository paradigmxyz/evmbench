from pydantic import BaseModel


class UserObject(BaseModel):
    avatar_url: str | None
    username: str
