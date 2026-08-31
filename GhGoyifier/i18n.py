# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
from __future__ import annotations

from typing import Any

langs = ("en", "ru", "uk", "kk", "de")
flags = {
    "ru": '<tg-emoji emoji-id="5449408995691341691">🇷🇺</tg-emoji>',
    "en": '<tg-emoji emoji-id="5202196682497859879">🇬🇧</tg-emoji>',
    "uk": '<tg-emoji emoji-id="5447309366568953338">🇺🇦</tg-emoji>',
    "kk": '<tg-emoji emoji-id="5228718354658769982">🇰🇿</tg-emoji>',
    "de": '<tg-emoji emoji-id="5409360418520967565">🇩🇪</tg-emoji>',
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
        "language.en": "English", "language.ru": "Russian", "language.uk": "Ukrainian", "language.kk": "Kazakh", "language.de": "German",
        "language.close": "✕ Close",
        "language.only_admin": "Only chat administrators can change the chat language.",
        "language.private_only": "This language setting is available only in private chat.",
        "language.current": "Current language: {name}",
        "events.title": "GitHub event settings",
        "events.stale": "Some events are not subscribed on GitHub. Run /reinstall.",
        "menu.connect": "Connect", "menu.add": "Add to chat", "menu.repos": "Repos", "menu.chats": "My chats", "menu.help": "Help", "menu.project": "GhGoyifier",
        "welcome": "<h2><b>Hi! I'm a Goyifier bot.</b></h2><p>I deliver GitHub notifications to Telegram using efficient polling.</p><hr><p><b>First step:</b> tap <b>Connect</b> below to authorize GitHub, then add me to a group and choose a repository.</p><details><summary>How setup works</summary><p>Authorize GitHub, choose a repository, select a chat, then configure event types.</p></details>",
        "help": "<h2><b>Goyifier help</b></h2><p>Use the buttons below for private-chat setup.</p><hr><details><summary>Private controls</summary><p><b>Connect</b> manages GitHub authorization.<br><b>Add to chat</b> invites the bot to a group.<br><b>Repos</b> browses repositories.<br><b>My chats</b> manages integrations.<br><b>Set language</b> changes this interface.</p></details><details><summary>Group commands</summary><p><code>/integrate owner/repo</code><br><code>/integrations</code><br><code>/events</code><br><code>/setlang</code><br><code>/set_topic</code><br><code>/reinstall</code><br><code>/remove owner/repo</code></p></details>",
    },
    "ru": {
        "language.title": "Выберите язык интерфейса",
        "language.saved": "Язык изменён на английский.",
        "language.saved_ru": "Язык изменён на русский.",
        "language.en": "Английский", "language.ru": "Русский", "language.uk": "Украинский", "language.kk": "Казахский", "language.de": "Немецкий",
        "language.close": "✕ Закрыть",
        "language.only_admin": "Только администраторы чата могут менять язык чата.",
        "language.private_only": "Эта настройка языка доступна только в личном чате.",
        "language.current": "Текущий язык: {name}",
        "events.title": "Настройки событий GitHub",
        "events.stale": "Некоторые события не подписаны в GitHub. Выполните /reinstall.",
        "menu.connect": "Подключить", "menu.add": "Добавить в чат", "menu.repos": "Репозитории", "menu.chats": "Мои чаты", "menu.help": "Помощь", "menu.project": "GhGoyifier",
        "welcome": "<h2><b>Привет! Я бот Goyifier.</b></h2><p>Я доставляю уведомления GitHub в Telegram через эффективный polling.</p><hr><p><b>Первый шаг:</b> нажми <b>Подключить</b>, авторизуй GitHub, затем добавь меня в группу и выбери репозиторий.</p><details><summary>Как это работает</summary><p>Авторизуй GitHub, выбери репозиторий и чат, затем настрой типы событий.</p></details>",
        "help": "<h2><b>Помощь Goyifier</b></h2><p>Используй кнопки ниже для настройки в личном чате.</p><hr><details><summary>Личные настройки</summary><p><b>Подключить</b> управляет авторизацией GitHub.<br><b>Добавить в чат</b> приглашает бота в группу.<br><b>Репозитории</b> показывает доступные репозитории.<br><b>Мои чаты</b> управляет интеграциями.<br><b>Язык</b> меняет язык интерфейса.</p></details><details><summary>Команды группы</summary><p><code>/integrate owner/repo</code><br><code>/integrations</code><br><code>/events</code><br><code>/setlang</code><br><code>/set_topic</code><br><code>/reinstall</code><br><code>/remove owner/repo</code></p></details>",
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
    return flags.get(normalize(lang), "")


def language_name(lang: str | None) -> str:
    language = normalize(lang)
    return tr(language, f"language.{language}")


labels.update({
    "uk": {"push": "Пуш", "pull_request": "Запит на злиття", "issues": "Задача", "issue_comment": "Коментар до задачі", "pull_request_review": "Перевірка запиту на злиття", "pull_request_review_comment": "Коментар до рядка запиту", "commit_comment": "Коментар до коміту", "release": "Реліз", "workflow_run": "Запуск Workflow", "deployment_status": "Розгортання", "discussion": "Обговорення", "discussion_comment": "Коментар до обговорення", "fork": "Форк", "star": "Зірка", "create": "Створення посилання", "delete": "Видалення посилання", "member": "Учасник репозиторію", "public": "Видимість репозиторію", "page_build": "Збірка Pages", "repository": "Репозиторій", "team": "Команда", "membership": "Членство", "organization": "Організація", "project": "Проєкт", "project_card": "Картка проєкту", "pull_request_review_thread": "Обговорення перевірки", "package": "Пакет", "workflow_job": "Завдання Workflow", "check_run": "Перевірка", "check_suite": "Набір перевірок", "status": "Статус коміту", "code_scanning": "Сповіщення аналізу коду", "secret_scanning": "Сповіщення пошуку секретів", "vulnerability_alert": "Сповіщення про вразливість", "security_advisory": "Рекомендація безпеки", "label": "Мітка", "milestone": "Етап", "branch_protection_rule": "Правило захисту гілки"},
    "kk": {"push": "Пуш", "pull_request": "Pull request", "issues": "Мәселе", "issue_comment": "Мәселе пікірі", "pull_request_review": "Pull request тексеруі", "pull_request_review_comment": "Pull request жол пікірі", "commit_comment": "Коммит пікірі", "release": "Релиз", "workflow_run": "Workflow іске қосылуы", "deployment_status": "Орналастыру", "discussion": "Талқылау", "discussion_comment": "Талқылау пікірі", "fork": "Fork", "star": "Жұлдыз", "create": "Сілтеме жасалды", "delete": "Сілтеме жойылды", "member": "Репозиторий мүшесі", "public": "Репозиторий көрінуі", "page_build": "Pages құрастырылымы", "repository": "Репозиторий", "team": "Команда", "membership": "Мүшелік", "organization": "Ұйым", "project": "Жоба", "project_card": "Жоба картасы", "pull_request_review_thread": "Pull request талқылауы", "package": "Пакет", "workflow_job": "Workflow тапсырмасы", "check_run": "Тексеру", "check_suite": "Тексерулер жиыны", "status": "Коммит күйі", "code_scanning": "Код талдауы ескертуі", "secret_scanning": "Құпияларды іздеу ескертуі", "vulnerability_alert": "Осалдық ескертуі", "security_advisory": "Қауіпсіздік кеңесі", "label": "Белгі", "milestone": "Кезең", "branch_protection_rule": "Бұтақ қорғау ережесі"},
    "de": {"push": "Push", "pull_request": "Pull Request", "issues": "Issue", "issue_comment": "Issue-Kommentar", "pull_request_review": "Pull-Request-Review", "pull_request_review_comment": "Pull-Request-Zeilenkommentar", "commit_comment": "Commit-Kommentar", "release": "Release", "workflow_run": "Workflow-Lauf", "deployment_status": "Deployment", "discussion": "Diskussion", "discussion_comment": "Diskussionskommentar", "fork": "Fork", "star": "Stern", "create": "Referenz erstellt", "delete": "Referenz gelöscht", "member": "Repository-Mitglied", "public": "Repository-Sichtbarkeit", "page_build": "Pages-Build", "repository": "Repository", "team": "Team", "membership": "Mitgliedschaft", "organization": "Organisation", "project": "Projekt", "project_card": "Projektkarte", "pull_request_review_thread": "Pull-Request-Review-Thread", "package": "Paket", "workflow_job": "Workflow-Aufgabe", "check_run": "Prüfung", "check_suite": "Prüfungsgruppe", "status": "Commit-Status", "code_scanning": "Code-Scanning-Warnung", "secret_scanning": "Secret-Scanning-Warnung", "vulnerability_alert": "Schwachstellenwarnung", "security_advisory": "Sicherheitshinweis", "label": "Label", "milestone": "Meilenstein", "branch_protection_rule": "Branch-Schutzregel"},
})

for _code, _names in {"uk": "Українська", "kk": "Қазақша", "de": "Deutsch"}.items():
    text[_code] = {
        "language.title": "Оберіть мову інтерфейсу" if _code == "uk" else "Интерфейс тілін таңдаңыз" if _code == "kk" else "Sprache auswählen",
        "language.saved": "Мову змінено на обрану." if _code == "uk" else "Тіл таңдалды." if _code == "kk" else "Sprache geändert.",
        "language.saved_ru": "Мову змінено на російську." if _code == "uk" else "Тіл орысшаға өзгертілді." if _code == "kk" else "Sprache auf Russisch geändert.",
        "language.en": "Англійська" if _code == "uk" else "Ағылшынша" if _code == "kk" else "English",
        "language.ru": "Російська" if _code == "uk" else "Орысша" if _code == "kk" else "Russisch",
        "language.uk": _names,
        "language.kk": _names,
        "language.de": _names,
        "language.close": "✕ Закрити" if _code == "uk" else "✕ Жабу" if _code == "kk" else "✕ Schließen",
        "language.only_admin": "Тільки адміністратори можуть змінювати мову чату." if _code == "uk" else "Чат тілін тек әкімшілер өзгерте алады." if _code == "kk" else "Nur Chat-Administratoren können die Chatsprache ändern.",
        "language.current": "Поточна мова: {name}" if _code == "uk" else "Ағымдағы тіл: {name}" if _code == "kk" else "Aktuelle Sprache: {name}",
        "events.title": "Налаштування подій GitHub" if _code == "uk" else "GitHub оқиғаларының баптаулары" if _code == "kk" else "GitHub-Ereigniseinstellungen",
        "events.stale": "Деякі події не підписані в GitHub. Виконайте /reinstall." if _code == "uk" else "Кейбір оқиғалар GitHub-та қосылмаған. /reinstall орындаңыз." if _code == "kk" else "Einige Ereignisse sind bei GitHub nicht abonniert. Führe /reinstall aus.",
        "menu.connect": "Підключити" if _code == "uk" else "Қосу" if _code == "kk" else "Verbinden",
        "menu.add": "Додати до чату" if _code == "uk" else "Чатқа қосу" if _code == "kk" else "Zum Chat hinzufügen",
        "menu.repos": "Репозиторії" if _code == "uk" else "Репозиторийлер" if _code == "kk" else "Repos",
        "menu.chats": "Мої чати" if _code == "uk" else "Чаттарым" if _code == "kk" else "Meine Chats",
        "menu.help": "Допомога" if _code == "uk" else "Көмек" if _code == "kk" else "Hilfe",
        "menu.project": "GhGoyifier",
    }
