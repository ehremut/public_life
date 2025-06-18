class InputFile:
    def __init__(self, file, filename=None):
        self.file = file
        self.filename = filename

class ReplyKeyboardMarkup:
    def __init__(self, keyboard, **kwargs):
        self.keyboard = keyboard
        self.kwargs = kwargs

class InlineKeyboardMarkup:
    def __init__(self, inline_keyboard):
        self.inline_keyboard = inline_keyboard

class InlineKeyboardButton:
    def __init__(self, text, callback_data=None):
        self.text = text
        self.callback_data = callback_data

class Message:
    def __init__(self, message_id=None):
        self.message_id = message_id

class Update:
    def __init__(self, effective_user=None, effective_chat=None, message=None, effective_message=None):
        self.effective_user = effective_user
        self.effective_chat = effective_chat
        self.message = message
        self.effective_message = effective_message or message
