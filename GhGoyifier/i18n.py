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
        "menu.connect": "Connect", "menu.add": "Add to chat", "menu.repos": "Repos", "menu.chats": "My chats", "menu.help": "Help", "menu.project": "GhGoyifier",
        "welcome": "<h2><b>Hi! I'm a Goyifier bot.</b></h2><p>I deliver GitHub notifications to Telegram using efficient polling.</p><hr><p><b>First step:</b> tap <b>Connect</b> below to authorize GitHub, then add me to a group and choose a repository.</p><details><summary>How setup works</summary><p>Authorize GitHub, choose a repository, select a chat, then configure event types.</p></details>",
        "help": "<h2><b>Goyifier help</b></h2><p>Use the buttons below for private-chat setup.</p><hr><details><summary>Private controls</summary><p><b>Connect</b> manages GitHub authorization.<br><b>Add to chat</b> invites the bot to a group.<br><b>Repos</b> browses repositories.<br><b>My chats</b> manages integrations.<br><b>Set language</b> changes this interface.</p></details><details><summary>Group commands</summary><p><code>/integrate owner/repo</code><br><code>/integrations</code><br><code>/events</code><br><code>/setlang</code><br><code>/set_topic</code><br><code>/reinstall</code><br><code>/delete owner/repo</code></p></details>",
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
        "menu.connect": "Подключить", "menu.add": "Добавить в чат", "menu.repos": "Репозитории", "menu.chats": "Мои чаты", "menu.help": "Помощь", "menu.project": "GhGoyifier",
        "welcome": "<h2><b>Привет! Я бот Goyifier.</b></h2><p>Я доставляю уведомления GitHub в Telegram через эффективный polling.</p><hr><p><b>Первый шаг:</b> нажми <b>Подключить</b>, авторизуй GitHub, затем добавь меня в группу и выбери репозиторий.</p><details><summary>Как это работает</summary><p>Авторизуй GitHub, выбери репозиторий и чат, затем настрой типы событий.</p></details>",
        "help": "<h2><b>Помощь Goyifier</b></h2><p>Используй кнопки ниже для настройки в личном чате.</p><hr><details><summary>Личные настройки</summary><p><b>Подключить</b> управляет авторизацией GitHub.<br><b>Добавить в чат</b> приглашает бота в группу.<br><b>Репозитории</b> показывает доступные репозитории.<br><b>Мои чаты</b> управляет интеграциями.<br><b>Язык</b> меняет язык интерфейса.</p></details><details><summary>Команды группы</summary><p><code>/integrate owner/repo</code><br><code>/integrations</code><br><code>/events</code><br><code>/setlang</code><br><code>/set_topic</code><br><code>/reinstall</code><br><code>/delete owner/repo</code></p></details>",
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
