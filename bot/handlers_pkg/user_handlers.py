"""Telegram command and callback handlers."""

import asyncio
import html
import uuid
from telegram import (
    Update,
    InputFile,
    ReplyKeyboardMarkup,
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from datetime import datetime
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
)

from config import config
from threexui.qr_utils import generate_qr
from vpn_service_client import get_vpn_service_client, XUIRequestError
from ..storage import UserStorage
from ..services.user_service import UserService
from .. import messages as msg

xui = get_vpn_service_client()

store = UserStorage()


async def _clean_chat(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    delete_update: bool = True,
) -> None:
    """Delete bot and user messages to keep chats tidy."""
    if is_admin(update.effective_user.id):
        return
    msg = update.effective_message
    if msg and delete_update:
        try:
            await msg.delete()
        except Exception:
            pass
    user_data = context.user_data if isinstance(getattr(context, "user_data", None), dict) else {}
    for mid in user_data.pop("bot_msgs", []):
        try:
            await context.bot.delete_message(update.effective_chat.id, mid)
        except Exception:
            continue


def _record(context: ContextTypes.DEFAULT_TYPE, message: Message) -> None:
    """Remember bot message IDs for later deletion."""
    mid = getattr(message, "message_id", None)
    if mid:
        user_data = context.user_data if isinstance(getattr(context, "user_data", None), dict) else None
        if isinstance(user_data, dict):
            user_data.setdefault("bot_msgs", []).append(mid)


async def _send_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, **kwargs) -> Message:
    """Send text and record its message ID."""
    msg = await context.bot.send_message(update.effective_chat.id, text, **kwargs)
    _record(context, msg)
    return msg


async def _send_photo(update: Update, context: ContextTypes.DEFAULT_TYPE, photo, **kwargs) -> Message:
    """Send photo and remember its message ID."""
    msg = await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo, **kwargs)
    _record(context, msg)
    return msg

MAIN_MENU = ReplyKeyboardMarkup(
    [[msg.BUTTON_CONFIG, msg.BUTTON_PROFILE]],
    resize_keyboard=True,
)

ADMIN_MENU = ReplyKeyboardMarkup(
    [
        [msg.BUTTON_CONFIG, msg.BUTTON_PROFILE],
        [msg.BUTTON_REQUESTS],
        [msg.BUTTON_USERS],
        [msg.BUTTON_APPROVE, msg.BUTTON_BLOCK],
        [msg.BUTTON_UNBLOCK, msg.BUTTON_DELETE],
        [msg.BUTTON_SENDCONFIG, msg.BUTTON_BROADCAST],
        [msg.BUTTON_MESSAGE],
    ],
    resize_keyboard=True,
)

service = UserService(xui, store, ADMIN_MENU, MAIN_MENU)

BACK_BUTTON = msg.BACK_BUTTON
OPEN_MENU = "open_menu"
USER_PREFIX = "user:"
LIST_USERS_DATA = "users"
WAITING_PREFIX = "wait:"
LIST_WAITING_DATA = "waiting"

CONFIG_OPTIONS = msg.CONFIG_OPTIONS

CONFIG_DAYS = {
    CONFIG_OPTIONS[0]: 7,
    CONFIG_OPTIONS[1]: 30,
    CONFIG_OPTIONS[2]: 90,
    CONFIG_OPTIONS[3]: 182,
    CONFIG_OPTIONS[4]: 365,
}

DAY_TO_OPTION = {v: k for k, v in CONFIG_DAYS.items()}

CONFIG_PREFIX = "cfg:"
BACK_DATA = "back"


def is_admin(user_id: int) -> bool:
    return service.is_admin(user_id)


def menu_for(user_id: int) -> ReplyKeyboardMarkup:
    return service.menu_for(user_id)


async def ensure_user(update: Update):
    """Create or fetch a user record for the current Telegram ID."""
    return await service.ensure_user(
        update.effective_user.id,
        update.effective_user.username or str(update.effective_user.id),
    )


async def send_link(update: Update, context: ContextTypes.DEFAULT_TYPE, link: str) -> None:
    """Send VLESS link and explanatory text."""
    text = msg.TEXTS["your_config"].format(link=html.escape(link))
    await _send_text(
        update,
        context,
        text,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the current user's VPN status."""
    await _clean_chat(update, context)
    tg_id = str(update.effective_user.id)
    try:
        user = await xui.get_user_by_remark(tg_id)
    except XUIRequestError as exc:
        await _send_text(
            update,
            context,
            str(exc),
            reply_markup=menu_for(update.effective_user.id),
        )
        return
    if user:
        link = await xui.get_vless_link(user)
        expire = user.get("expiryTime")
        if isinstance(expire, (int, float)):

            if expire > 1_000_000_000_000:
                expire /= 1000
            expire = datetime.fromtimestamp(expire).strftime("%Y-%m-%d %H:%M")
        else:
            expire = str(expire)
        text = f"Режим активен до {expire}.\n<code>{html.escape(link)}</code>"
        await _send_text(
            update,
            context,
            text,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=menu_for(update.effective_user.id),
        )
    else:
        await _send_text(
            update,
            context,
            msg.TEXTS["no_active"],
            reply_markup=menu_for(update.effective_user.id),
        )


async def get_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send the user's current VPN configuration as text and QR."""
    await _clean_chat(update, context)
    tg_id = str(update.effective_user.id)
    try:
        user = await xui.get_user_by_remark(tg_id)
    except XUIRequestError as exc:
        await _send_text(update, context, str(exc))
        return
    if not user:
        await _send_text(
            update,
            context,
            msg.TEXTS["no_active"],
            reply_markup=menu_for(update.effective_user.id),
        )
        return
    link = await xui.get_vless_link(user)
    qr = await asyncio.to_thread(generate_qr, link)
    await _send_photo(update, context, InputFile(qr, filename="qr.png"))
    await send_link(update, context, link)
    await _send_text(
        update,
        context,
        msg.TEXTS["menu"],
        reply_markup=menu_for(update.effective_user.id),
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command and show the main menu."""
    await _clean_chat(update, context, delete_update=False)
    await ensure_user(update)
    text = msg.TEXTS["welcome"]
    await _send_text(
        update,
        context,
        text,
        reply_markup=menu_for(update.effective_user.id),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a list of available commands."""
    await _clean_chat(update, context)
    user = await ensure_user(update)
    lines = [
        "/start - меню",
        "/account - профиль",
        "/profile - профиль",
        "/config - выбор конфигурации",
    ]
    if is_admin(user.user_id):
        lines.extend(
            [
                "/users - список пользователей",
                "/approve ID - одобрить доступ",
                "/block ID - блокировать",
                "/unblock ID - разблокировать",
                "/delete ID - удалить",
                "/sendconfig ID - отправить конфигурацию",
                "/waiting - список заявок",
                "/reject ID - отклонить заявку",
                "/message ID текст - сообщение пользователю",
                "/broadcast текст - сообщение всем",
            ]
        )
    await _send_text(
        update,
        context,
        msg.TEXTS["help_header"].format(cmds="\n".join(lines)),
        reply_markup=menu_for(user.user_id),
    )


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display user profile with current status and config info."""
    await _clean_chat(update, context)
    user = await ensure_user(update)
    status_map = msg.STATUS_MAP
    status = status_map.get(user.status, user.status)
    text = msg.TEXTS["profile_header"].format(
        username=user.username,
        user_id=user.user_id,
        status=status,
    )
    if user.days:
        text += msg.TEXTS["profile_active"].format(
            option=DAY_TO_OPTION.get(user.days, f"{user.days} дн.")
        )
    req = user.request_days
    if req:
        text += msg.TEXTS["profile_requested"].format(
            option=DAY_TO_OPTION.get(req, f"{req} дн.")
        )

    link = None
    if user.xui_id:
        try:
            xui_user = await xui.get_user_by_id(user.xui_id)
        except XUIRequestError:
            xui_user = None
        if xui_user:
            link = await xui.get_vless_link(xui_user)
            expire = xui_user.get("expiryTime")
            if isinstance(expire, (int, float)):
                if expire > 1_000_000_000_000:
                    expire /= 1000
                expire = datetime.fromtimestamp(expire).strftime("%Y-%m-%d %H:%M")
            else:
                expire = str(expire)
            text += msg.TEXTS["profile_expire"].format(expire=expire)
    buttons = []
    if user.role != "approved" and not is_admin(user.user_id):
        buttons.append([
            InlineKeyboardButton(msg.REQUEST_ACCESS_BUTTON, callback_data="request_access")
        ])
    buttons.append([InlineKeyboardButton(BACK_BUTTON, callback_data=BACK_DATA)])
    await _send_text(
        update,
        context,
        text,
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    if link:
        qr = await asyncio.to_thread(generate_qr, link)
        await _send_photo(update, context, InputFile(qr, filename="qr.png"))
        await send_link(update, context, link)

async def request_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Submit a configuration request to all admins."""
    query = getattr(update, "callback_query", None)
    if query:
        await query.answer()
    await _clean_chat(update, context)
    user = await ensure_user(update)
    if is_admin(user.user_id):
        await _send_text(update, context, msg.TEXTS["already_have_access"])
        return
    if user.role == "approved" and user.status == "active":
        await _send_text(update, context, msg.TEXTS["already_approved"])
        return
    days = user.request_days
    if not days:
        buttons = [[InlineKeyboardButton("Меню", callback_data=OPEN_MENU)]]
        await _send_text(
            update,
            context,
            msg.TEXTS["select_config_first"],
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return
    if user.status == "awaiting":
        await _send_text(update, context, msg.TEXTS["already_requested"])
        return
    await store.update(user, status="awaiting")
    text = msg.TEXTS["request_fmt"].format(
        username=user.username,
        user_id=user.user_id,
        option=f"{days} дн."
    )
    for admin_id in config.admin_ids:
        await context.bot.send_message(admin_id, text)
    await _send_text(
        update,
        context,
        msg.TEXTS["request_sent"],
        reply_markup=menu_for(user.user_id),
    )


async def choose_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt the user to select a configuration duration."""
    await _clean_chat(update, context)
    await ensure_user(update)
    buttons = [
        [InlineKeyboardButton(opt, callback_data=f"{CONFIG_PREFIX}{CONFIG_DAYS[opt]}")]
        for opt in CONFIG_OPTIONS
    ]
    buttons.append([InlineKeyboardButton(BACK_BUTTON, callback_data=BACK_DATA)])
    await _send_text(
        update,
        context,
        msg.TEXTS["choose_config"],
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def send_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle configuration choice callbacks."""
    query = update.callback_query
    if query:
        await query.answer()
    await _clean_chat(update, context)
    data = query.data if query else ""
    if data == BACK_DATA:
        await _send_text(
            update,
            context,
            msg.TEXTS["menu"],
            reply_markup=menu_for(update.effective_user.id),
        )
        return
    if not data.startswith(CONFIG_PREFIX):
        return
    try:
        days = int(data.split(":", 1)[1])
    except ValueError:
        await _send_text(update, context, "Неизвестный вариант")
        return
    option = DAY_TO_OPTION.get(days, f"{days} дн.")
    user = await ensure_user(update)
    if days is None:
        await _send_text(update, context, "Неизвестный вариант")
        return
    if is_admin(user.user_id):
        if user.xui_id:
            try:
                await xui.update_user(user.xui_id, days, ip_limit=4)
                xui_user = await xui.get_user_by_id(user.xui_id)
            except XUIRequestError as exc:
                await _send_text(update, context, str(exc))
                return
            remark = xui_user.get("remark", user.remark or "")
        else:
            custom_id = f"{user.username}_{user.config_counter + 1}_{uuid.uuid4().hex[:5]}"
            remark = f"{user.username}_{uuid.uuid4().hex[:8]}"
            try:
                xui_user = await xui.create_user(
                    remark=remark,
                    days=days,
                    tg_id=str(user.user_id),
                    ip_limit=4,
                    custom_id=custom_id,
                    username=user.username,
                )
            except XUIRequestError as exc:
                try:
                    existing = await xui.get_user_by_remark(str(user.user_id))
                except XUIRequestError:
                    existing = None
                if existing:
                    try:
                        await xui.update_user(existing["id"], days, ip_limit=4)
                    except XUIRequestError as exc2:
                        await _send_text(update, context, str(exc2))
                        return
                    xui_user = existing
                    remark = existing.get("remark", remark)
                else:
                    await _send_text(update, context, str(exc))
                    return
        link = await xui.get_vless_link(xui_user)
        qr = await asyncio.to_thread(generate_qr, link)
        await _send_photo(update, context, InputFile(qr, filename="qr.png"))
        await send_link(update, context, link)
        await store.update(
            user,
            days=days,
            remark=remark,
            xui_id=xui_user.get("id"),
            config_counter=user.config_counter + 1,
        )
        await _send_text(
            update,
            context,
            msg.TEXTS["menu"],
            reply_markup=menu_for(user.user_id),
        )
        return
    if user.role != "approved" or user.status != "active":
        await store.update(user, request_days=days, status="awaiting")
    else:
        await store.update(user, request_days=days)
    text = msg.TEXTS["request_fmt"].format(
        username=user.username,
        user_id=user.user_id,
        option=option,
    )
    for admin_id in config.admin_ids:
        await context.bot.send_message(admin_id, text)
    await _send_text(
        update,
        context,
        msg.TEXTS["request_sent"],
        reply_markup=menu_for(user.user_id),
    )
    await _send_text(
        update,
        context,
        "Меню:",
        reply_markup=menu_for(user.user_id),
    )
    return


async def renew_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process manual renewal days input from admin."""
    await _clean_chat(update, context)
    try:
        days = int(update.message.text)
    except ValueError:
        await _send_text(update, context, msg.TEXTS["need_number"])
        return ConversationHandler.END
    user_id = context.user_data.get("user_id")
    if user_id is None:
        await _send_text(update, context, msg.TEXTS["unknown_error"])
        return ConversationHandler.END
    try:
        await xui.renew_user(user_id, days)
    except XUIRequestError as exc:
        await _send_text(update, context, str(exc))
        return ConversationHandler.END
    user = await xui.get_user_by_id(user_id)
    link = await xui.get_vless_link(user) if user else ""
    if link:
        qr = await asyncio.to_thread(generate_qr, link)
        await _send_photo(update, context, InputFile(qr, filename="qr.png"))
        await send_link(update, context, link)
    else:
        await _send_text(update, context, msg.TEXTS["updated"])
    return ConversationHandler.END


async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all registered users in an inline keyboard."""
    if not is_admin(update.effective_user.id):
        return
    buttons = [
        [
            InlineKeyboardButton(
                f"@{u.username} ({u.user_id})",
                callback_data=f"{USER_PREFIX}{u.user_id}",
            )
        ]
        for u in await store.list_all()
    ]
    if not buttons:
        buttons.append([InlineKeyboardButton(msg.TEXTS["no_users"], callback_data="noop")])
    await _clean_chat(update, context)
    await _send_text(
        update,
        context,
        msg.TEXTS["choose_user"],
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def list_waiting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List users waiting for approval."""
    if not is_admin(update.effective_user.id):
        return
    waiting = [
        u
        for u in await store.list_all()
        if u.request_days and not is_admin(u.user_id)
    ]
    buttons = [
        [
            InlineKeyboardButton(
                f"@{u.username} ({u.user_id})",
                callback_data=f"{WAITING_PREFIX}{u.user_id}",
            )
        ]
        for u in waiting
    ]
    if not buttons:
        buttons.append([InlineKeyboardButton(msg.TEXTS["no_requests"], callback_data="noop")])
    buttons.append([InlineKeyboardButton(msg.INLINE_BACK, callback_data=OPEN_MENU)])
    await _clean_chat(update, context)
    await _send_text(
        update,
        context,
        msg.TEXTS["requests_header"],
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def show_waiting_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display approve/reject buttons for a pending request."""
    query = update.callback_query
    if query:
        await query.answer()
    if not is_admin(update.effective_user.id):
        return
    try:
        uid = int((query.data or "")[len(WAITING_PREFIX):])
    except ValueError:
        return
    user = await store.get(uid)
    if not user or not user.request_days or is_admin(uid):
        return
    buttons = [
        [InlineKeyboardButton(msg.INLINE_APPROVE, callback_data=f"approve:{uid}")],
        [InlineKeyboardButton(msg.INLINE_REJECT, callback_data=f"reject:{uid}")],
        [InlineKeyboardButton(msg.INLINE_BACK, callback_data=LIST_WAITING_DATA)],
    ]
    await _clean_chat(update, context)
    await _send_text(
        update,
        context,
        msg.TEXTS["request_from"].format(uid=uid),
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def show_user_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show management actions for a specific user."""
    query = update.callback_query
    if query:
        await query.answer()
    if not is_admin(update.effective_user.id):
        return
    try:
        uid = int((query.data or "")[len(USER_PREFIX):])
    except ValueError:
        return
    rec = await store.get(uid)
    buttons = []
    if rec:
        if rec.request_days:
            buttons.append([InlineKeyboardButton(msg.INLINE_APPROVE, callback_data=f"approve:{uid}")])
            buttons.append([InlineKeyboardButton(msg.INLINE_REJECT, callback_data=f"reject:{uid}")])
        if rec.status != "blocked":
            buttons.append([InlineKeyboardButton(msg.INLINE_BLOCK, callback_data=f"block:{uid}")])
        if rec.status == "blocked":
            buttons.append([InlineKeyboardButton(msg.INLINE_UNBLOCK, callback_data=f"unblock:{uid}")])
        buttons.append([InlineKeyboardButton(msg.INLINE_DELETE, callback_data=f"delete:{uid}")])
        if rec.xui_id:
            buttons.append([
                InlineKeyboardButton(
                    msg.INLINE_SENDCONF, callback_data=f"sendconfig:{uid}"
                )
            ])
            buttons.append(
                [
                    InlineKeyboardButton(
                        msg.INLINE_GETCONF, callback_data=f"getconfig:{uid}"
                    )
                ]
            )
        buttons.append(
            [InlineKeyboardButton(msg.INLINE_SENDMSG, callback_data=f"sendmsg:{uid}")]
        )
    buttons.append([InlineKeyboardButton(msg.INLINE_BACK, callback_data=LIST_USERS_DATA)])
    await _clean_chat(update, context)
    await _send_text(
        update,
        context,
        msg.TEXTS["actions_for"].format(uid=uid),
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def perform_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route inline button callbacks to the appropriate action."""
    query = update.callback_query
    if query:
        await query.answer()
    if not is_admin(update.effective_user.id):
        return
    parts = (query.data or "").split(":", 1)
    if len(parts) != 2:
        return
    action, uid = parts
    context.args = [uid]
    if action == "approve":
        await approve(update, context)
    elif action == "block":
        await block(update, context)
    elif action == "unblock":
        await unblock(update, context)
    elif action == "delete":
        await delete(update, context)
    elif action == "sendconfig":
        await sendconfig(update, context, to_user=True)
    elif action == "getconfig":
        await sendconfig(update, context, to_user=False)
    elif action == "sendmsg":
        await prompt_message(update, context, uid)
    elif action == "reject":
        await reject(update, context)


async def list_users_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    await list_users(update, context)


async def list_waiting_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    await list_waiting(update, context)


async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Approve a user's request and create their VPN account."""
    await _clean_chat(update, context)
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await _send_text(
            update,
            context,
            msg.TEXTS["need_id"],
            reply_markup=menu_for(update.effective_user.id),
        )
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        await _send_text(
            update,
            context,
            msg.TEXTS["invalid_id"],
            reply_markup=menu_for(update.effective_user.id),
        )
        return
    user = await store.get(uid)
    if not user:
        await _send_text(
            update,
            context,
            msg.TEXTS["user_not_found"],
            reply_markup=menu_for(update.effective_user.id),
        )
        return
    days = user.request_days
    if not days:
        await _send_text(
            update,
            context,
            msg.TEXTS["no_request_from_user"],
            reply_markup=menu_for(update.effective_user.id),
        )
        return
    remark = user.remark or f"{user.username}_{uuid.uuid4().hex[:8]}"
    custom_id = f"{user.username}_{user.config_counter + 1}_{uuid.uuid4().hex[:5]}"
    if user.xui_id:
        try:
            await xui.update_user(user.xui_id, days, ip_limit=4)
            xui_user = await xui.get_user_by_id(user.xui_id)
        except XUIRequestError as exc:
            await _send_text(update, context, str(exc))
            return
    else:
        try:
            xui_user = await xui.create_user(
                remark=remark,
                days=days,
                tg_id=str(uid),
                ip_limit=4,
                custom_id=custom_id,
                username=user.username,
            )
        except XUIRequestError as exc:
            try:
                existing = await xui.get_user_by_remark(str(uid))
            except XUIRequestError:
                existing = None
            if existing:
                try:
                    await xui.update_user(existing["id"], days, ip_limit=4)
                except XUIRequestError as exc2:
                    await _send_text(update, context, str(exc2))
                    return
                xui_user = existing
            else:
                await _send_text(update, context, str(exc))
                return
    link = await xui.get_vless_link(xui_user)
    qr = await asyncio.to_thread(generate_qr, link)
    await context.bot.send_photo(uid, InputFile(qr, filename="qr.png"))
    await context.bot.send_message(
        uid,
        msg.TEXTS["your_config"].format(link=html.escape(link)),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    await store.update(
        user,
        role="approved",
        status="active",
        request_days=0,
        days=days,
        remark=remark,
        xui_id=xui_user.get("id"),
        config_counter=user.config_counter + 1,
    )
    await _send_text(
        update,
        context,
        msg.TEXTS["done"],
        reply_markup=menu_for(update.effective_user.id),
    )


async def reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reject a pending access request."""
    await _clean_chat(update, context)
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await _send_text(update, context, msg.TEXTS["need_id"], reply_markup=menu_for(update.effective_user.id))
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        await _send_text(update, context, msg.TEXTS["invalid_id"], reply_markup=menu_for(update.effective_user.id))
        return
    user = await store.get(uid)
    if not user:
        await _send_text(update, context, msg.TEXTS["user_not_found"], reply_markup=menu_for(update.effective_user.id))
        return
    if not user.request_days:
        await _send_text(update, context, msg.TEXTS["no_request"], reply_markup=menu_for(update.effective_user.id))
        return
    await store.update(user, request_days=0)
    try:
        await context.bot.send_message(uid, msg.TEXTS["rejected_to_user"])
    except Exception:
        pass
    await _send_text(update, context, msg.TEXTS["rejected"], reply_markup=menu_for(update.effective_user.id))


async def block(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Block a user's VPN account."""
    await _clean_chat(update, context)
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await _send_text(update, context, msg.TEXTS["need_id"], reply_markup=menu_for(update.effective_user.id))
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        await _send_text(update, context, msg.TEXTS["invalid_id"], reply_markup=menu_for(update.effective_user.id))
        return
    user = await store.get(uid)
    if not user:
        await _send_text(update, context, msg.TEXTS["user_not_found"], reply_markup=menu_for(update.effective_user.id))
        return
    await store.update(user, status="blocked")
    try:
        if user.xui_id:
            await xui.set_enable(user.xui_id, False)
    except XUIRequestError as exc:
        await _send_text(update, context, str(exc))
        return
    await context.bot.send_message(uid, msg.TEXTS["blocked_msg"])
    await _send_text(update, context, msg.TEXTS["done"], reply_markup=menu_for(update.effective_user.id))


async def unblock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unblock a previously blocked user."""
    await _clean_chat(update, context)
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await _send_text(update, context, msg.TEXTS["need_id"], reply_markup=menu_for(update.effective_user.id))
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        await _send_text(update, context, msg.TEXTS["invalid_id"], reply_markup=menu_for(update.effective_user.id))
        return
    user = await store.get(uid)
    if not user:
        await _send_text(update, context, msg.TEXTS["user_not_found"], reply_markup=menu_for(update.effective_user.id))
        return
    if user.status != "blocked":
        await _send_text(update, context, msg.TEXTS["user_not_blocked"], reply_markup=menu_for(update.effective_user.id))
        return
    if user.xui_id:
        try:
            await xui.set_enable(user.xui_id, True)
        except XUIRequestError as exc:
            await _send_text(update, context, str(exc), reply_markup=menu_for(update.effective_user.id))
            return
        await store.update(user, status="active")
    else:
        await store.update(user, status="awaiting")
    try:
        await context.bot.send_message(uid, msg.TEXTS["unblocked_msg"])
    except Exception:
        pass
    await _send_text(update, context, msg.TEXTS["done"], reply_markup=menu_for(update.effective_user.id))


async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a user's VPN account and local record."""
    await _clean_chat(update, context)
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await _send_text(update, context, msg.TEXTS["need_id"], reply_markup=menu_for(update.effective_user.id))
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        await _send_text(update, context, msg.TEXTS["invalid_id"], reply_markup=menu_for(update.effective_user.id))
        return
    user = await store.get(uid)
    if user:
        await store.delete(uid)
    try:
        if user and user.xui_id:
            await xui.delete_user(user.xui_id)
    except XUIRequestError as exc:
        await _send_text(update, context, str(exc), reply_markup=menu_for(update.effective_user.id))
        return
    await _send_text(update, context, msg.TEXTS["deleted"], reply_markup=menu_for(update.effective_user.id))


async def sendconfig(update: Update, context: ContextTypes.DEFAULT_TYPE, *, to_user: bool = False):
    """Send the selected configuration to one user or broadcast."""
    await _clean_chat(update, context)
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await _send_text(update, context, msg.TEXTS["need_id"], reply_markup=menu_for(update.effective_user.id))
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        await _send_text(update, context, msg.TEXTS["invalid_id"], reply_markup=menu_for(update.effective_user.id))
        return
    rec = await store.get(uid)
    if not rec or not rec.xui_id:
        await _send_text(update, context, msg.TEXTS["not_found"], reply_markup=menu_for(update.effective_user.id))
        return
    try:
        user = await xui.get_user_by_id(rec.xui_id)
    except XUIRequestError as exc:
        await _send_text(update, context, str(exc), reply_markup=menu_for(update.effective_user.id))
        return
    if not user:
        await _send_text(update, context, msg.TEXTS["not_found"], reply_markup=menu_for(update.effective_user.id))
        return
    link = await xui.get_vless_link(user)
    qr = await asyncio.to_thread(generate_qr, link)
    chat_id = uid if to_user else update.effective_chat.id
    await context.bot.send_photo(chat_id, InputFile(qr, filename="qr.png"))
    await context.bot.send_message(
        chat_id,
        msg.TEXTS["your_config"].format(link=html.escape(link)),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    if to_user:
        await _send_text(update, context, msg.TEXTS["sent"], reply_markup=menu_for(update.effective_user.id))
    else:
        await _send_text(update, context, msg.TEXTS["menu"], reply_markup=menu_for(update.effective_user.id))


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a text message to all users."""
    await _clean_chat(update, context)
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await _send_text(update, context, msg.TEXTS["need_message"], reply_markup=menu_for(update.effective_user.id))
        return
    text = " ".join(context.args)
    for rec in await store.list_all():
        try:
            await context.bot.send_message(rec.user_id, text)
        except Exception:
            continue
    await _send_text(update, context, msg.TEXTS["sent"], reply_markup=menu_for(update.effective_user.id))


async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask admin for a message then send it to a user."""
    await _clean_chat(update, context)
    if not is_admin(update.effective_user.id):
        return
    if len(context.args) < 2:
        await _send_text(update, context, msg.TEXTS["need_id_message"], reply_markup=menu_for(update.effective_user.id))
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        await _send_text(update, context, msg.TEXTS["invalid_id"], reply_markup=menu_for(update.effective_user.id))
        return
    text = " ".join(context.args[1:])
    try:
        await context.bot.send_message(uid, text)
    except Exception as exc:
        await _send_text(update, context, str(exc), reply_markup=menu_for(update.effective_user.id))
        return
    await _send_text(update, context, msg.TEXTS["sent"], reply_markup=menu_for(update.effective_user.id))


async def prompt_message(update: Update, context: ContextTypes.DEFAULT_TYPE, uid: str) -> None:
    """Handle the next admin message and deliver it to ``uid``."""
    await _clean_chat(update, context)
    context.user_data["msg_uid"] = int(uid)
    await _send_text(
        update,
        context,
        msg.TEXTS["prompt_message"].format(uid=uid),
    )


async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text responses when waiting for admin input."""
    if not is_admin(update.effective_user.id):
        return
    uid = context.user_data.pop("msg_uid", None)
    if uid is None:
        return
    await _clean_chat(update, context)
    try:
        await context.bot.send_message(uid, update.message.text)
    except Exception as exc:
        await _send_text(update, context, str(exc), reply_markup=menu_for(update.effective_user.id))
        return
    await _send_text(update, context, msg.TEXTS["sent"], reply_markup=menu_for(update.effective_user.id))


async def open_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return to the main reply keyboard."""
    query = update.callback_query
    if query:
        await query.answer()
    await _clean_chat(update, context)
    await _send_text(
        update,
        context,
        msg.TEXTS["menu"],
        reply_markup=menu_for(update.effective_user.id),
    )





async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reply when the user enters an unknown command."""
    await _clean_chat(update, context)
    await _send_text(update, context, msg.TEXTS["unknown_command"], reply_markup=menu_for(update.effective_user.id))


def setup(app):
    """Register all handlers with a ``telegram.ext.Application`` instance."""
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("account", profile))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("users", list_users))
    app.add_handler(CommandHandler("approve", approve))
    app.add_handler(CommandHandler("block", block))
    app.add_handler(CommandHandler("unblock", unblock))
    app.add_handler(CommandHandler("delete", delete))
    app.add_handler(CommandHandler("sendconfig", sendconfig))
    app.add_handler(CommandHandler("waiting", list_waiting))
    app.add_handler(CommandHandler("reject", reject))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("message", message))
    app.add_handler(CallbackQueryHandler(list_users_cb, pattern=f"^{LIST_USERS_DATA}$"))
    app.add_handler(CallbackQueryHandler(show_user_actions, pattern=rf"^{USER_PREFIX}\d+$"))
    app.add_handler(CallbackQueryHandler(list_waiting_cb, pattern=f"^{LIST_WAITING_DATA}$"))
    app.add_handler(CallbackQueryHandler(show_waiting_actions, pattern=rf"^{WAITING_PREFIX}\d+$"))
    app.add_handler(CallbackQueryHandler(perform_action, pattern=r"^(?:approve|block|unblock|delete|sendconfig|getconfig|sendmsg|reject):\d+$"))
    app.add_handler(CallbackQueryHandler(request_access, pattern="^request_access$"))
    app.add_handler(CallbackQueryHandler(open_menu, pattern=f"^{OPEN_MENU}$"))
    app.add_handler(MessageHandler(filters.Regex("^👤 Профиль$"), profile))
    app.add_handler(MessageHandler(filters.Regex("^🔐 Выбрать конфигурацию$"), choose_config))
    app.add_handler(MessageHandler(filters.Regex("^🕓 Заявки$"), list_waiting))
    app.add_handler(CommandHandler("config", choose_config))
    app.add_handler(CallbackQueryHandler(send_config, pattern=rf"^(?:{CONFIG_PREFIX}\d+|{BACK_DATA})$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.User(config.admin_ids), handle_admin_text))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))
