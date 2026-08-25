# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
from __future__ import annotations

import os
import stat
from pathlib import Path

_private_file_mode = 0o600
_private_dir_mode = 0o700


def _regular_file(path: Path) -> None:
    if path.is_symlink():
        raise PermissionError(f"Refusing symlink for secret-bearing file: {path}")
    if not path.is_file():
        raise FileNotFoundError(path)
    info = path.stat()
    if info.st_uid != os.getuid():
        raise PermissionError(f"Secret-bearing file is not owned by current user: {path}")
    if not stat.S_ISREG(info.st_mode):
        raise PermissionError(f"Secret-bearing path is not a regular file: {path}")
    path.chmod(_private_file_mode)


def _private_dir(path: Path) -> None:
    path.mkdir(mode=_private_dir_mode, parents=True, exist_ok=True)
    if path.is_symlink():
        raise PermissionError(f"Refusing symlink for secret-bearing directory: {path}")
    info = path.stat()
    if info.st_uid != os.getuid() or not stat.S_ISDIR(info.st_mode):
        raise PermissionError(f"Secret-bearing directory is unsafe: {path}")
    path.chmod(_private_dir_mode)


def harden_config_file(config_file: str) -> Path:
    path = Path(config_file).expanduser().resolve()
    _regular_file(path)
    return path


def harden_runtime(config_file: str, config) -> None:
    os.umask(0o077)
    harden_config_file(config_file)

    db_path = Path(config.database.file_name).expanduser()
    if not db_path.is_absolute():
        db_path = Path.cwd() / db_path
    _private_dir(db_path.parent)
    if db_path.exists():
        _regular_file(db_path)
    for suffix in ("-wal", "-shm", "-journal"):
        sidecar = Path(str(db_path) + suffix)
        if sidecar.exists():
            _regular_file(sidecar)

    private_key = str(config.github_app.private_key_path or "").strip()
    if private_key:
        key_path = Path(private_key).expanduser()
        if not key_path.is_absolute():
            key_path = Path.cwd() / key_path
        if key_path.exists():
            _private_dir(key_path.parent)
            _regular_file(key_path)
