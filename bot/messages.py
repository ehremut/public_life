from typing import Final

# Button labels
BUTTON_CONFIG: Final = "🔐 Выбрать конфигурацию"
BUTTON_PROFILE: Final = "👤 Профиль"
BUTTON_REQUESTS: Final = "🕓 Заявки"
BUTTON_USERS: Final = "/users 👥"
BUTTON_APPROVE: Final = "/approve"
BUTTON_BLOCK: Final = "/block"
BUTTON_UNBLOCK: Final = "/unblock"
BUTTON_DELETE: Final = "/delete"
BUTTON_SENDCONFIG: Final = "/sendconfig"
BUTTON_BROADCAST: Final = "/broadcast"
BUTTON_MESSAGE: Final = "/message"
BACK_BUTTON: Final = "↩️ Назад"
REQUEST_ACCESS_BUTTON: Final = "Запросить доступ"

# Configuration option labels
CONFIG_OPTIONS: Final = [
    "🗓 1 неделя",
    "📅 1 месяц",
    "📅 3 месяца",
    "📆 Полгода",
    "🗓 Год",
]

# Inline button labels
INLINE_APPROVE: Final = "Одобрить"
INLINE_REJECT: Final = "Отклонить"
INLINE_BLOCK: Final = "Блокировать"
INLINE_UNBLOCK: Final = "Разблокировать"
INLINE_DELETE: Final = "Удалить"
INLINE_SENDCONF: Final = "Отправить конфигурацию"
INLINE_GETCONF: Final = "Получить конфигурацию"
INLINE_SENDMSG: Final = "Написать сообщение"
INLINE_BACK: Final = "⬅️ Назад"

# Text messages
TEXTS: Final = {
    "welcome": "Добро пожаловать! Используйте меню для работы с подключением. Для списка команд введите /help.",
    "help_header": "Доступные команды:\n{cmds}",
    "menu": "Меню:",
    "choose_config": "Выберите конфигурацию:",
    "select_config_first": "Сначала выберите конфигурацию через меню.",
    "already_requested": "Заявка уже отправлена. Ожидайте подтверждения.",
    "request_sent": "Ваша заявка на подключение отправлена. Ожидайте подтверждения.",
    "your_config": "Ваш конфиг:\n<code>{link}</code>",
    "need_number": "Нужно ввести число",
    "unknown_error": "Неизвестная ошибка",
    "updated": "Обновлено",
    "no_users": "Нет пользователей",
    "choose_user": "Выберите пользователя:",
    "no_requests": "Нет заявок",
    "requests_header": "Заявки:",
    "request_fmt": "📥 Заявка от @{username} (ID: {user_id}). Конфигурация: {option}. Статус: ожидает подтверждения.",
    "request_from": "Заявка от {uid}:",
    "actions_for": "Действия для {uid}:",
    "profile_header": "Имя пользователя: {username}\nID: {user_id}\nСтатус доступа: {status}",
    "profile_active": "\nАктивный вариант: {option}",
    "profile_requested": "\nЗапрошенный вариант: {option}",
    "profile_expire": "\nДействует до {expire}",
    "need_id": "Нужен ID",
    "invalid_id": "Неверный ID",
    "user_not_found": "Пользователь не найден",
    "no_request": "Нет заявки",
    "no_request_from_user": "Нет запроса от пользователя",
    "already_have_access": "У вас уже есть доступ.",
    "already_approved": "Доступ уже подтверждён.",
    "no_active": "У вас нет активного режима.",
    "rejected_to_user": "Ваша заявка отклонена",
    "rejected": "Отклонено",
    "blocked_msg": "Доступ заблокирован",
    "unblocked_msg": "Доступ восстановлен",
    "user_not_blocked": "Пользователь не заблокирован",
    "done": "Готово",
    "deleted": "Удалено",
    "not_found": "Не найдено",
    "need_message": "Нужно сообщение",
    "sent": "Отправлено",
    "need_id_message": "Нужен ID и сообщение",
    "prompt_message": "Введите сообщение для пользователя {uid}:",
    "unknown_command": "Неизвестная команда",
}

STATUS_MAP: Final = {
    "active": "активен",
    "awaiting": "ожидает",
    "blocked": "заблокирован",
}
