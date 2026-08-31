import re

_repo_pattern = re.compile(
    r"(?:https?://)?(?:[\w.-]+\.)?github(?:usercontent)?\.com/"
    r"(?:repos/)?"
    r"(?P<owner>[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?!-))*[a-zA-Z0-9])"
    r"/"
    r"(?P<repo>[a-zA-Z0-9._](?:[a-zA-Z0-9._]|-(?!-))*[a-zA-Z0-9._])",
    re.IGNORECASE,
)


def normalize_repo(raw: str) -> str:
    raw = raw.strip().rstrip("/")
    m = _repo_pattern.search(raw)
    if m:
        return f"{m.group('owner')}/{m.group('repo')}"
    if raw.count("/") == 1:
        return raw
    return raw
