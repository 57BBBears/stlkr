import validators
from flask_wtf import FlaskForm
from wtforms import TextAreaField, SubmitField, ValidationError, SelectField, SelectMultipleField
from wtforms_alchemy import model_form_factory
from app import db
from app.core.models import DataFrame, Check, Cluster
from app.core.utils import text_to_list


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
        only = ['name', 'selectors']

    submit = SubmitField('Запустить')


class ClusterAddForm(ModelForm):
    # TODO add js to ClusterForm to fill slug while name editing instead of this form
    class Meta:
        model = Cluster
        only = ['name', 'title', 'description', 'excerpt', 'text', 'image']

    parent_id = SelectField('Parent cluster', coerce=int)

    submit = SubmitField('Добавить')


class ClusterForm(ModelForm):
    class Meta:
        model = Cluster
        only = ['name', 'slug', 'title', 'description', 'excerpt', 'text', 'image']

    parent_id = SelectField('Parent cluster', coerce=int)
    frames = SelectMultipleField(coerce=str)

    submit = SubmitField('Сохранить')


