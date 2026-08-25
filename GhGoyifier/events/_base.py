# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
# Portions derived from vsecoder/github-notifi-bot; original MIT license is retained in LICENSE.
"""Shared Pydantic models — types that appear in multiple event payloads."""

from pydantic import BaseModel, ConfigDict


class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class GitHubUser(_Base):
    login: str
    html_url: str | None = None
    id: int | None = None


class Repository(_Base):
    full_name: str
    name: str | None = None
    html_url: str
    private: bool = False
    stargazers_count: int = 0
    forks: int = 0


class BranchRef(_Base):
    ref: str | None = None
    sha: str | None = None


class Issue(_Base):
    number: int
    title: str
    html_url: str
    user: GitHubUser
    body: str | None = None
    pull_request: dict | None = None


class PullRequest(_Base):
    number: int
    title: str
    html_url: str
    user: GitHubUser
    body: str | None = None
    merged: bool | None = None
    base: BranchRef | None = None
    head: BranchRef | None = None
    additions: int | None = None
    deletions: int | None = None
    changed_files: int | None = None


class Comment(_Base):
    body: str | None = None
    html_url: str
    user: GitHubUser
    path: str | None = None


class Discussion(_Base):
    number: int
    title: str
    html_url: str
    body: str | None = None
    user: GitHubUser
