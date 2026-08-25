from __future__ import annotations

import asyncio
import logging
import os
import re
import subprocess
import toml
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import aiohttp

_proxy_names = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "all_proxy", "no_proxy")
_proxy_schemes = {"http", "https", "socks4", "socks4a", "socks5", "socks5h"}


def _masked_url(value: str) -> str:
    parsed = urlsplit(value)
    if not parsed.hostname:
        return value
    host = parsed.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    netloc = host
    if parsed.port:
        netloc += f":{parsed.port}"
    if parsed.username:
        netloc = f"{parsed.username}:***@{netloc}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


def validate_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    if parsed.scheme.lower() not in _proxy_schemes or not parsed.hostname or not parsed.port:
        raise ValueError("proxy URL must use http, https, socks4, socks4a, socks5, or socks5h with host and port")
    if not 1 <= parsed.port <= 65535:
        raise ValueError("proxy port must be between 1 and 65535")
    return value.strip()


def _read_system_environment() -> dict[str, str]:
    values = {name: os.environ[name] for name in _proxy_names if os.environ.get(name)}
    files = [Path("/etc/environment"), Path.home() / ".config" / "environment.d" / "90-goyifier-proxy.conf"]
    directory = Path.home() / ".config" / "environment.d"
    if directory.is_dir():
        files.extend(sorted(directory.glob("*.conf")))
    assignment = re.compile(r"^\s*(?:export\s+)?(" + "|".join(_proxy_names) + r")\s*=\s*(.*?)\s*$")
    for path in files:
        try:
            for line in path.read_text(errors="replace").splitlines():
                match = assignment.match(line)
                if match:
                    value = match.group(2)
                    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                        value = value[1:-1]
                    values[match.group(1)] = value
        except OSError:
            continue
    try:
        runtime_dir = Path(f"/run/user/{os.getuid()}")
        env = os.environ.copy()
        env.setdefault("XDG_RUNTIME_DIR", str(runtime_dir))
        bus = runtime_dir / "bus"
        if bus.exists():
            env.setdefault("DBUS_SESSION_BUS_ADDRESS", f"unix:path={bus}")
        result = subprocess.run(["systemctl", "--user", "show-environment"], text=True, capture_output=True, timeout=2, check=False, env=env)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                match = assignment.match(line)
                if match:
                    values[match.group(1)] = match.group(2)
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        mode = subprocess.run(["gsettings", "get", "org.gnome.system.proxy", "mode"], text=True, capture_output=True, timeout=2, check=False)
        if mode.returncode == 0 and mode.stdout.strip().strip("'") == "manual":
            for scheme in ("http", "https"):
                host = subprocess.run(["gsettings", "get", f"org.gnome.system.proxy.{scheme}", "host"], text=True, capture_output=True, timeout=2, check=False)
                port = subprocess.run(["gsettings", "get", f"org.gnome.system.proxy.{scheme}", "port"], text=True, capture_output=True, timeout=2, check=False)
                proxy_host = host.stdout.strip().strip("'")
                proxy_port = port.stdout.strip().split()[-1] if port.stdout.strip() else ""
                if host.returncode == 0 and port.returncode == 0 and proxy_host and proxy_host != "''" and proxy_port.isdigit() and proxy_port != "0":
                    values[f"{scheme.upper()}_PROXY"] = f"http://{proxy_host}:{proxy_port}"
    except (OSError, subprocess.SubprocessError):
        pass
    return values


def _profiles(path: str) -> tuple[dict, list[dict]]:
    data = toml.load(path) if Path(path).exists() else {}
    section = data.get("proxy") or {}
    profiles = []
    for item in section.get("profiles") or []:
        if not isinstance(item, dict) or not item.get("name") or not item.get("url"):
            continue
        try:
            url = validate_url(str(item["url"]))
        except ValueError:
            continue
        profiles.append({"name": str(item["name"]), "url": url, "enabled": bool(item.get("enabled", True)), "priority": int(item.get("priority", 100))})
    return section, profiles


class ProxyManager:
    def __init__(self, app, config_path: str):
        self.app = app
        self.config_path = config_path
        self.current: dict | None = None
        self.candidates: list[dict] = []
        self.index = -1
        self.signature: tuple = ()
        self.lock = asyncio.Lock()

    async def run(self) -> None:
        while True:
            try:
                await self.refresh()
            except asyncio.CancelledError:
                raise
            except Exception:
                logging.getLogger("goyifi.proxy").exception("Proxy refresh failed; waiting before retry")
            await asyncio.sleep(5)

    async def refresh(self) -> None:
        async with self.lock:
            section, profiles = _profiles(self.config_path)
            auto = bool(section.get("auto", True))
            active = str(section.get("active") or "")
            candidates = []
            if active:
                candidates.extend(item for item in profiles if item["name"] == active and item["enabled"])
            candidates.extend(item for item in sorted(profiles, key=lambda item: (item["priority"], item["name"])) if item["enabled"] and item not in candidates)
            system = _read_system_environment() if auto and not candidates else {}
            signature = (auto, active, tuple((item["name"], item["url"], item["enabled"], item["priority"]) for item in profiles), tuple(sorted(system.items())))
            if signature == self.signature:
                return
            self.signature = signature
            self.candidates = candidates
            self.index = -1
            if candidates:
                await self._apply(candidates[0])
            else:
                await self._apply_environment(system)

    async def failover(self) -> None:
        async with self.lock:
            if not self.candidates:
                return
            next_index = self.index + 1
            if next_index >= len(self.candidates):
                next_index = 0
            await self._apply(self.candidates[next_index], next_index)

    async def _apply(self, profile: dict, index: int | None = None) -> None:
        self.index = self.candidates.index(profile) if index is None else index
        await self._apply_url(profile["url"])
        self.current = profile

    async def _apply_environment(self, values: dict[str, str]) -> None:
        system_url = values.get("ALL_PROXY") or values.get("all_proxy")
        if system_url and urlsplit(system_url).scheme.lower().startswith("socks"):
            await self._apply_url(system_url)
            return
        for name in _proxy_names:
            if values.get(name):
                os.environ[name] = values[name]
            else:
                os.environ.pop(name, None)
        await self._reset_session(None)
        self.current = None

    async def _apply_url(self, url: str) -> None:
        scheme = urlsplit(url).scheme.lower()
        for name in _proxy_names:
            os.environ.pop(name, None)
        if scheme in {"http", "https"}:
            os.environ["HTTP_PROXY"] = url
            os.environ["HTTPS_PROXY"] = url
            await self._reset_session(None)
            return
        try:
            from aiohttp_socks import ProxyConnector
        except ImportError as exc:
            raise RuntimeError("SOCKS proxy support requires aiohttp-socks") from exc
        connector = ProxyConnector.from_url(url.replace("socks5h://", "socks5://", 1))
        await self._reset_session(aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=35), trust_env=False))

    async def _reset_session(self, replacement) -> None:
        bot = getattr(self.app, "bot", None)
        if bot is None:
            return
        session = getattr(bot, "sess", None)
        if session is not None and not session.closed:
            await session.close()
        bot.sess = replacement

    def status(self) -> dict:
        return {"current": self.current, "candidates": self.candidates, "index": self.index}


__all__ = ["ProxyManager", "_masked_url", "_profiles", "_proxy_schemes", "validate_url"]
