# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
from __future__ import annotations

from typing import Any

langs = ("en", "ru")
flags = {
    "ru": '<tg-emoji emoji-id="5449408995691341691">🇷🇺</tg-emoji>',
    "en": '<tg-emoji emoji-id="5202196682497859879">🇬🇧</tg-emoji>',
}
labels = {
    "en": {
        "push": "Push", "pull_request": "Pull request", "issues": "Issue", "issue_comment": "Issue comment",
        "pull_request_review": "Pull request review", "pull_request_review_comment": "Pull request review comment",
        "commit_comment": "Commit comment", "release": "Release", "workflow_run": "Workflow run",
        "deployment_status": "Deployment", "discussion": "Discussion", "discussion_comment": "Discussion comment",
        "fork": "Fork", "star": "Star", "create": "Reference created", "delete": "Reference deleted",
        "member": "Repository member", "public": "Repository visibility", "page_build": "Pages build",
        "repository": "Repository", "team": "Team", "membership": "Membership", "organization": "Organization",
        "project": "Project", "project_card": "Project card", "pull_request_review_thread": "Pull request review thread",
        "package": "Package", "workflow_job": "Workflow job", "check_run": "Check run", "check_suite": "Check suite",
        "status": "Commit status", "code_scanning": "Code scanning alert", "secret_scanning": "Secret scanning alert",
        "vulnerability_alert": "Vulnerability alert", "security_advisory": "Security advisory", "label": "Label",
        "milestone": "Milestone", "branch_protection_rule": "Branch protection rule",
    },
    "ru": {
        "push": "Отправка коммитов", "pull_request": "Запрос на слияние", "issues": "Задача", "issue_comment": "Комментарий к задаче",
        "pull_request_review": "Проверка запроса на слияние", "pull_request_review_comment": "Комментарий к строке запроса",
        "commit_comment": "Комментарий к коммиту", "release": "Релиз", "workflow_run": "Запуск Workflow",
        "deployment_status": "Развёртывание", "discussion": "Обсуждение", "discussion_comment": "Комментарий к обсуждению",
        "fork": "Ответвление", "star": "Звезда", "create": "Создание ссылки", "delete": "Удаление ссылки",
        "member": "Участник репозитория", "public": "Видимость репозитория", "page_build": "Сборка Pages",
        "repository": "Репозиторий", "team": "Команда", "membership": "Членство", "organization": "Организация",
        "project": "Проект", "project_card": "Карточка проекта", "pull_request_review_thread": "Обсуждение проверки",
        "package": "Пакет", "workflow_job": "Задача Workflow", "check_run": "Проверка", "check_suite": "Набор проверок",
        "status": "Статус коммита", "code_scanning": "Оповещение анализа кода", "secret_scanning": "Оповещение поиска секретов",
        "vulnerability_alert": "Оповещение уязвимости", "security_advisory": "Рекомендация безопасности", "label": "Метка",
        "milestone": "Этап", "branch_protection_rule": "Правило защиты ветки",
    },
}
text = {
    "en": {
        "language.title": "Choose interface language",
        "language.saved": "Language changed to English.",
        "language.saved_ru": "Language changed to Russian.",
        "language.en": "English",
        "language.ru": "Russian",
        "language.close": "✕ Close",
        "language.only_admin": "Only chat administrators can change the chat language.",
        "language.private_only": "This language setting is available only in private chat.",
        "language.current": "Current language: {name}",
        "events.title": "GitHub event settings",
        "events.stale": "Some events are not subscribed on GitHub. Run /reinstall.",
    },
    "ru": {
        "language.title": "Выберите язык интерфейса",
        "language.saved": "Язык изменён на английский.",
        "language.saved_ru": "Язык изменён на русский.",
        "language.en": "Английский",
        "language.ru": "Русский",
        "language.close": "✕ Закрыть",
        "language.only_admin": "Только администраторы чата могут менять язык чата.",
        "language.private_only": "Эта настройка языка доступна только в личном чате.",
        "language.current": "Текущий язык: {name}",
        "events.title": "Настройки событий GitHub",
        "events.stale": "Некоторые события не подписаны в GitHub. Выполните /reinstall.",
    },
}


def normalize(value: str | None) -> str:
    return value if value in langs else "en"


def tr(lang: str | None, key: str, **kwargs: Any) -> str:
    language = normalize(lang)
    value = text.get(language, {}).get(key) or text["en"].get(key) or key
    return value.format(**kwargs)


def event_label(lang: str | None, event: str) -> str:
    language = normalize(lang)
    return labels.get(language, labels["en"]).get(event, event)


def flag(lang: str) -> str:
    return flags[normalize(lang)]


def language_name(lang: str | None) -> str:
    language = normalize(lang)
    return tr(language, "language.ru" if language == "ru" else "language.en")
