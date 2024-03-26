from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import data_required#, Email, equal_to, ValidationError, EqualTo


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[data_required()])
    password = PasswordField('Password', validators=[data_required()])
    remember_me = BooleanField('Remember me')
    submit = SubmitField('Login')

"""
class RegistrationForm(FlaskForm):
    username = StringField(_l('Username'), validators=[data_required()])
    email = EmailField(_l('Email'), validators=[data_required(), Email()])
    password = PasswordField(_l('Password'), validators=[data_required()])
    password1 = PasswordField(_l('Repeat password'), validators=[data_required(), equal_to('password')])
    submit = SubmitField(_l('Register'))

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError(_l('This name already exists'))

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError(_l('This email already exists'))


class ResetPasswordForm(FlaskForm):
    email = StringField(_l('Email'), validators=[data_required(), Email()])
    submit = SubmitField(_l('Send'))


class ResetPasswordConfirmForm(FlaskForm):
    password = PasswordField(_l('Password'), validators=[data_required()])
    password1 = PasswordField(
        _l('Repeat password'), validators=[data_required(), EqualTo('password')])
    submit = SubmitField(_l('Change password'))
"""