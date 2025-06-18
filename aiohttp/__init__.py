class ClientError(Exception):
    pass

class ClientSession:
    def __init__(self):
        self.closed = False
    async def get(self, *a, **kw):
        raise ClientError("not implemented")
    async def post(self, *a, **kw):
        raise ClientError("not implemented")
    async def close(self):
        self.closed = True
