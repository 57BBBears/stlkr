from wtforms import ValidationError

from src.models import db
from src.services.dao.user import UserDAO


def email_registered(message: str | None = None):
    message = message or "Email не найден"

    def wrapper(form, field):
        dao = UserDAO(db.session)

        if not dao.get_by_email(field.data.lower()):
            raise ValidationError(message)

    return wrapper


def email_not_registered(message: str | None = None):
    message = message or "Email занят"

    def wrapper(form, field):
        dao = UserDAO(db.session)

        if dao.get_by_email(field.data.lower()):
            raise ValidationError(message)

    return wrapper
