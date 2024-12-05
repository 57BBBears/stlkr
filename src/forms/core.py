from flask_wtf import FlaskForm, RecaptchaField
from wtforms import BooleanField, EmailField, PasswordField, StringField, SubmitField
from wtforms.validators import email, equal_to, input_required, length

from src.forms.validators import email_not_registered, email_registered


class RegisterForm(FlaskForm):
    name = StringField("Имя", validators=[input_required(), length(max=255)])
    email = StringField(
        "Email",
        validators=[input_required(), email(), length(max=255), email_not_registered()],
    )
    password = PasswordField("Пароль", validators=[input_required(), length(max=255)])
    confirm = PasswordField(
        "Повторите пароль",
        validators=[
            input_required(),
            length(max=255),
            equal_to("password", message="Пароли не совпадают"),
        ],
    )
    recaptcha = RecaptchaField()
    submit = SubmitField("Зарегистрироваться")


class LoginForm(FlaskForm):
    login = StringField(
        "Email",
        validators=[input_required(), email(), email_registered(), length(max=255)],
    )
    password = PasswordField("Пароль", validators=[input_required(), length(max=255)])
    # recaptcha = RecaptchaField()
    remember_me = BooleanField("Запомнить меня")
    submit = SubmitField("Войти")


class ResetPasswordForm(FlaskForm):
    email = EmailField(
        "Email",
        validators=[input_required(), email(), email_registered(), length(max=255)],
    )
    recaptcha = RecaptchaField()
    submit = SubmitField("Восстановить")


class ChangePasswordForm(FlaskForm):
    password = PasswordField("Пароль", [input_required(), length(max=255)])
    confirm = PasswordField(
        "Повторите пароль",
        validators=[
            input_required(),
            length(max=255),
            equal_to("password", message="Пароли не совпадают"),
        ],
    )
    recaptcha = RecaptchaField()
    submit = SubmitField("Изменить пароль")
