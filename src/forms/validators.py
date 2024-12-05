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


def max_file_size(max_size_kb):
    max_bytes = max_size_kb * 1024

    def file_length_check(form, field):
        if len(field.data.read()) > max_bytes:
            raise ValidationError(f"File size must be less than {max_size_kb} Kb")
        field.data.seek(0)

    return file_length_check
