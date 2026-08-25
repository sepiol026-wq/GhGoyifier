# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
from __future__ import annotations

import hashlib
import hmac
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

_prefix = "enc:v1:"
_key: bytes | None = None
_fernet: Fernet | None = None


def initialize() -> None:
    global _key, _fernet
    supplied = os.environ.get("GOYIFIER_DATA_KEY", "").strip()
    if supplied:
        key = supplied.encode()
    else:
        credential_dir = os.environ.get("CREDENTIALS_DIRECTORY", "").strip()
        configured_path = os.environ.get("GOYIFIER_DATA_KEY_FILE", "").strip()
        path = Path(configured_path or (Path(credential_dir) / "data.key" if credential_dir else "secrets/data.key")).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.parent.chmod(0o700)
        if path.exists():
            if path.is_symlink() or path.stat().st_uid != os.getuid():
                raise PermissionError(f"Unsafe data encryption key file: {path}")
            path.chmod(0o600)
            key = path.read_bytes().strip()
        else:
            key = Fernet.generate_key()
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            fd = os.open(path, flags, 0o600)
            try:
                os.write(fd, key)
            finally:
                os.close(fd)
    try:
        cipher = Fernet(key)
    except Exception as exc:
        raise ValueError("GOYIFIER_DATA_KEY must be a valid Fernet key") from exc
    _key = key
    _fernet = cipher


def _get_cipher() -> Fernet:
    if _fernet is None:
        initialize()
    assert _fernet is not None
    return _fernet


def is_encrypted(value: str | None) -> bool:
    return bool(value and value.startswith(_prefix))


def encrypt(value: str) -> str:
    if is_encrypted(value):
        return value
    return _prefix + _get_cipher().encrypt(value.encode()).decode()


def decrypt(value: str | None) -> str | None:
    if value is None or not is_encrypted(value):
        return value
    try:
        return _get_cipher().decrypt(value[len(_prefix) :].encode()).decode()
    except (InvalidToken, UnicodeDecodeError) as exc:
        raise ValueError("Encrypted application secret cannot be decrypted") from exc


def digest(value: str) -> str:
    key = _key
    if key is None:
        initialize()
        key = _key
    assert key is not None
    return hmac.new(key, value.encode(), hashlib.sha256).hexdigest()


def encrypted_length(value: str) -> int:
    return len(encrypt(value))
