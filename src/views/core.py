from functools import partial

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_user, logout_user
from werkzeug.routing import BuildError
from werkzeug.wrappers.response import Response

from config import Config
from src.forms.core import (
    ChangePasswordForm,
    LoginForm,
    RegisterForm,
    ResetPasswordForm,
)
from src.services.core.base import get_user
from src.services.core.change_password import change_user_password, get_email_by_token
from src.services.core.register import register_user
from src.services.core.reset_password import send_reset_password_link

bp = Blueprint("core", __name__)
route = partial(bp.route, host=Config.CORE_DOMAIN)


@route("/", methods=["GET", "POST"])
def index_view():
    form = LoginForm()

    if form.validate_on_submit():
        if (user := get_user(form.login.data)) and user.is_correct_password(
            form.password.data
        ):
            if login_user(user, remember=form.remember_me.data):
                return _get_redirect("projects.index_view")

        flash("Неверный email или пароль.", "danger")

    return render_template("core/index.html", form=form, title="[stlkr]")


@route("/register/", methods=["GET", "POST"])
def register_view():
    form = RegisterForm()

    if form.validate_on_submit():
        register_user(form.name.data, form.email.data, form.password.data)
        flash("Вы успешно зарегистрированы.", "success")

        return redirect(url_for("projects.index_view"))

    return render_template("core/index.html", form=form, title="Регистрация")


def _get_redirect(endpoint: str) -> Response:
    try:
        url = url_for(request.args.get("next"))
    except (BuildError, TypeError):
        return redirect(url_for(endpoint))
    else:
        return redirect(url)


@route("/reset-password/", methods=["GET", "POST"])
def reset_password_view():
    title = "Сброс пароля"
    form = ResetPasswordForm()

    if form.validate_on_submit():
        if user := get_user(form.email.data.lower()):
            send_reset_password_link(user.email, title)
            flash("Ссылка для сброса пароля отправлена на Ваш email.")

            return redirect(url_for("core.index"))

    return render_template("public/reset_password.html", form=form, title=title)


@route("/reset-password/<token>/", methods=["GET", "POST"])
def change_password_view(token: str):
    email = get_email_by_token(token)

    form = ChangePasswordForm()

    if form.validate_on_submit():
        change_user_password(email, form.password.data)

        flash("Пароль успешно изменён. Войдите используя новый пароль.", "success")

        return redirect(url_for("public.index"))

    return render_template(
        "public/change_password.html",
        form=form,
        token=token,
        title="Изменение пароля",
    )


@route("/logout/")
def logout_view():
    logout_user()

    return redirect(url_for("core.index"))
