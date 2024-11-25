class DAOError(Exception):
    def __init__(self, message: str | None = None):
        message = message or "Ошибка базы данных."

        super().__init__(message)


class IntegrityError(DAOError): ...
