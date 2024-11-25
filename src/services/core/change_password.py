from flask import current_app

from src.models import db
from src.services.auth.security import get_url_serializer
from src.services.dao.user import UserDAO

_24HOURS = 86400


def get_email_by_token(token: str, max_age: int = _24HOURS) -> str:
    url_serializer = get_url_serializer(current_app.config["SECRET_KEY"])

    return url_serializer.loads(
        token, salt=current_app.config["RESET_PASSWORD_SALT"], max_age=max_age
    )


def change_user_password(email: str, new_password: str):
    dao = UserDAO(db.session)

    user = dao.get_by_email(email)
    user.password = new_password

    dao.commit()
