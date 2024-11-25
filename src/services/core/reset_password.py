from flask import current_app, render_template, url_for

from src.services.auth.security import get_url_serializer
from src.services.mail import send_email


def send_reset_password_link(email: str, subject: str = "Сброс пароля"):
    html = _get_email_html(email)

    send_email(email, subject, html)


def _get_email_html(email: str) -> str:
    token = _get_reset_password_token(email)
    change_password_url = url_for("core.change_password", token=token, _external=True)

    return render_template(
        "email/reset_password.html", change_password_url=change_password_url
    )


def _get_reset_password_token(email: str) -> str | bytes:
    url_serializer = get_url_serializer(current_app.config["SECRET_KEY"])
    return url_serializer.dumps(email, salt=current_app.config["RESET_PASSWORD_SALT"])
