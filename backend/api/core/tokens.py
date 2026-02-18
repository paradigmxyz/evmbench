from datetime import UTC, datetime, timedelta

import jwt
from pydantic import BaseModel, ConfigDict, ValidationError

from api.core.config import settings


ALGORITHM = 'HS256'


class Token(BaseModel):
    model_config = ConfigDict(extra='forbid')

    user_id: str
    login: str
    avatar_url: str | None


class TokenClaims(Token):
    exp: int


def encode_token(token: Token) -> str:
    exp = datetime.now(tz=UTC) + timedelta(seconds=settings.BACKEND_JWT_TTL_SECONDS)
    payload = token.model_dump(mode='json') | {'exp': int(exp.timestamp())}
    return jwt.encode(payload, settings.BACKEND_JWT_SECRET.get_secret_value(), algorithm=ALGORITHM)


def decode_token(token: str) -> Token | None:
    try:
        payload = jwt.decode(
            token,
            key=settings.BACKEND_JWT_SECRET.get_secret_value(),
            algorithms=[ALGORITHM],
            options={'require': ['exp']},
        )
    except jwt.PyJWTError:
        return None

    try:
        claims = TokenClaims.model_validate(payload)
    except ValidationError:
        return None

    try:
        return Token.model_validate(
            claims.model_dump(mode='json', exclude={'exp'}),
        )
    except ValidationError:
        return None
