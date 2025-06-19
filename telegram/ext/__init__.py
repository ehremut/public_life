class ContextTypes:
    DEFAULT_TYPE = object

class _Filter:
    def __and__(self, other):
        return self
    def __or__(self, other):
        return self
    def __invert__(self):
        return self

class Filters(_Filter):
    def __init__(self):
        self.TEXT = self
        self.COMMAND = self

    @staticmethod
    def Regex(pattern):
        return Filters()

    @staticmethod
    def User(ids):
        return Filters()

class CommandHandler:
    def __init__(self, command, callback):
        self.command = command
        self.callback = callback

class MessageHandler:
    def __init__(self, filters, callback):
        self.filters = filters
        self.callback = callback

class CallbackQueryHandler:
    def __init__(self, callback, pattern=None):
        self.callback = callback
        self.pattern = pattern

class ConversationHandler:
    END = -1
    def __init__(self, *a, **kw):
        pass

class Application:
    def __init__(self):
        self.handlers = []
    @classmethod
    def builder(cls):
        class Builder:
            def __init__(self):
                self._token = None
            def token(self, token):
                self._token = token
                return self
            def build(self):
                return Application()
        return Builder()
    def add_handler(self, handler):
        self.handlers.append(handler)
    def run_polling(self, drop_pending_updates=False):
        pass

filters = Filters()
