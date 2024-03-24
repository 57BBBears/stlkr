import validators
from flask_wtf import FlaskForm
from wtforms import TextAreaField, SubmitField, ValidationError, SelectField, SelectMultipleField, BooleanField,\
    FieldList, FormField, StringField, HiddenField
from wtforms import validators
from wtforms_alchemy import model_form_factory, QuerySelectField
from app import db
from app.models import Dataframe, Check, Cluster, Property
from app.core.utils import text_to_list


BaseModelForm = model_form_factory(FlaskForm)

class ModelForm(BaseModelForm):
    @classmethod
    def get_session(cls):
        return db.session

class DataFrameForm(ModelForm):
    class Meta:
        model = Dataframe

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
        only = ['name']

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

class PropertyForm(ModelForm):
    class Meta:
        csrf = False

    id = HiddenField('')
    name = StringField('', [validators.Length(max=50)])
    code = StringField('', [validators.Length(max=50)])
    delete = BooleanField('')

    def validate_name(self, field):
        if not field.data and self.code.data:
            raise ValidationError('Обязательное поле')
    def validate_code(self, field):
        if not field.data and self.name.data:
            raise ValidationError('Обязательное поле')

class PropertiesForm(FlaskForm):
    properties = FieldList(FormField(PropertyForm))

    submit = SubmitField('Сохранить')


class DataFrameSelectorForm(FlaskForm):
    class Meta:
        csrf = False
    id = HiddenField('')
    property = StringField('', [validators.Length(max=50)], render_kw={'readonly': True})
    selector = StringField('', [validators.Length(max=50)])
    """
    property = QuerySelectField(query_factory=lambda: Property.query,
                                get_pk=lambda item: item.id,
                                get_label=lambda item: item.name,
                                allow_blank=True)
    """

    """
    def validate_property(self, field):
        if self.selector.data and not field.data:
            raise ValidationError('Обязательное поле')
    """

class DataFrameSelectorsForm(ModelForm):
    selectors = FieldList(FormField(DataFrameSelectorForm))

    submit = SubmitField('Сохранить')