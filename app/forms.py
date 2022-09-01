import validators
from flask_wtf import FlaskForm
from wtforms import TextAreaField, SubmitField, ValidationError
from wtforms_alchemy import model_form_factory
from app import db
from app.models import DataFrame, Check
from app.utils import text_to_list


BaseModelForm = model_form_factory(FlaskForm)


class ModelForm(BaseModelForm):
    @classmethod
    def get_session(cls):
        return db.session


class DataFrameForm(ModelForm):
    class Meta:
        model = DataFrame

    urls = TextAreaField('Ссылки')
    submit = SubmitField('Сохранить')

    def validate_urls(self, field):
        url_list = text_to_list(field.data)
        not_urls = []
        for url in url_list:
            if not validators.url(url):
                not_urls.append(url)
        if not_urls:
            raise ValidationError(f'Это не ссылки: {", ".join(not_urls)}')


class EmptyForm(FlaskForm):
    button = SubmitField('')


class DataFrameCheckForm(ModelForm):
    class Meta:
        model = Check
        include = ['name']

    submit = SubmitField('Запустить')
