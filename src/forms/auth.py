from flask_wtf import FlaskForm, RecaptchaField
from wtforms import BooleanField, EmailField, PasswordField, StringField, SubmitField
from wtforms.validators import email, equal_to, input_required

from src.forms.validators import email_not_registered, email_registered


class RegistrationForm(FlaskForm):
    email = StringField(
        "Email", validators=[input_required(), email(), email_not_registered()]
    )
    password = (PasswordField("Пароль", validators=[input_required()]),)
    confirm = (PasswordField("Повторите пароль", validators=[input_required()]),)
    recaptcha = (RecaptchaField(),)
    submit = SubmitField("Зарегистрироваться")


class LoginForm(FlaskForm):
    login = StringField(
        "Email", validators=[input_required(), email(), email_registered()]
    )
    password = PasswordField("Пароль", validators=[input_required()])
    recaptcha = RecaptchaField()
    remember_me = BooleanField("Запомнить меня")
    submit = SubmitField("Войти")


class ResetPasswordForm(FlaskForm):
    email = EmailField(
        "Email", validators=[input_required(), email(), email_registered()]
    )
    recaptcha = RecaptchaField()
    submit = SubmitField("Восстановить")


class ChangePasswordForm(FlaskForm):
    password = PasswordField("Пароль", [input_required()])
    confirm = PasswordField(
        "Повторите пароль",
        validators=[
            input_required(),
            equal_to("password", message="Пароли не совпадают"),
        ],
    )
    recaptcha = RecaptchaField()
    submit = SubmitField("Изменить пароль")
