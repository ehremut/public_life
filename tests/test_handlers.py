import unittest
from unittest.mock import AsyncMock, patch

from bot import handlers
from threexui.api import XUIRequestError


class HandlerErrorTests(unittest.IsolatedAsyncioTestCase):
    async def test_status_api_error(self):
        update = AsyncMock()
        update.effective_user.id = 1
        update.effective_chat.id = 1
        update.message = AsyncMock()
        update.effective_message = update.message
        context = AsyncMock()
        context.bot.send_message = AsyncMock()

        with patch.object(handlers.xui, "get_user_by_remark", AsyncMock(side_effect=XUIRequestError("boom"))):
            await handlers.status(update, context)

        self.assertEqual(context.bot.send_message.call_args.args[1], "boom")

    async def test_get_link_api_error(self):
        update = AsyncMock()
        update.effective_user.id = 1
        update.effective_chat.id = 1
        update.message = AsyncMock()
        update.effective_message = update.message
        context = AsyncMock()
        context.bot.send_message = AsyncMock()
        context.bot.send_photo = AsyncMock()

        with patch.object(handlers.xui, "get_user_by_remark", AsyncMock(side_effect=XUIRequestError("err"))):
            await handlers.get_link(update, context)

        self.assertEqual(context.bot.send_message.call_args.args[1], "err")

    async def test_renew_days_api_error(self):
        update = AsyncMock()
        update.message = AsyncMock()
        update.message.text = "5"
        update.effective_chat.id = 1
        update.effective_message = update.message
        context = AsyncMock()
        context.bot.send_message = AsyncMock()
        context.user_data = {'user_id': 2}

        with patch.object(handlers.xui, "renew_user", AsyncMock(side_effect=XUIRequestError("err"))):
            result = await handlers.renew_days(update, context)

        self.assertEqual(context.bot.send_message.call_args.args[1], "err")
        self.assertEqual(result, handlers.ConversationHandler.END)


if __name__ == "__main__":
    unittest.main()
