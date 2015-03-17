class TowelError(Exception):
    pass


class BadTextData(TowelError):
    def __init__(self, message):
        self.message = message
        super(BadTextData, self).__init__()
