from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_user, logout_user
from werkzeug.security import check_password_hash

from src.auth.forms import LoginForm
from src.models import User

bp = Blueprint("auth", __name__, template_folder="templates")


@bp.route("/login/", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        if user is None or not check_password_hash(user.password, form.password.data):
            flash("Please check your login details and try again.")
            return redirect(url_for("auth.login"))

        login_user(user, remember=form.remember_me.data)

        return redirect(url_for("auth.login"))

    return render_template(
        "auth/login.html",
        title="Login",
        form=form,
        is_auth=current_user.is_authenticated,
    )


@bp.route("/logout/")
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
