import base64
import binascii
import hashlib
import os

from Crypto.Cipher import AES


NONCE_SIZE_BYTES = 12
TAG_SIZE_BYTES = 16
VALID_KEY_LENGTHS = {16, 24, 32}


def _b64decode(value: str) -> bytes:
    normalized = value.strip()
    padding = '=' * (-len(normalized) % 4)
    return base64.urlsafe_b64decode(normalized + padding)


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode('ascii').rstrip('=')


def derive_key(value: str) -> bytes:
    digest = hashlib.sha512(value.encode('utf-8')).digest()
    return digest[:32]


def encrypt_token(plaintext: str, *, key: bytes, nonce: bytes | None = None) -> str:
    if nonce is None:
        nonce = os.urandom(NONCE_SIZE_BYTES)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext.encode('utf-8'))
    return _b64encode(nonce + ciphertext + tag)


def decrypt_token(token: str, *, key: bytes) -> str:
    try:
        payload = _b64decode(token)
    except binascii.Error as err:
        msg = 'Invalid token encoding'
        raise ValueError(msg) from err
    if len(payload) <= NONCE_SIZE_BYTES + TAG_SIZE_BYTES:
        msg = 'Invalid token payload'
        raise ValueError(msg)

    nonce = payload[:NONCE_SIZE_BYTES]
    ciphertext = payload[NONCE_SIZE_BYTES:-TAG_SIZE_BYTES]
    tag = payload[-TAG_SIZE_BYTES:]

    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    plaintext = cipher.decrypt_and_verify(ciphertext, tag)
    try:
        return plaintext.decode('utf-8')
    except UnicodeDecodeError as err:
        msg = 'Invalid token payload'
        raise ValueError(msg) from err
