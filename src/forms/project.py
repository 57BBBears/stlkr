from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    HiddenField,
)
from wtforms_alchemy import model_form_factory

from src.models import Extract, db

BaseModelForm = model_form_factory(FlaskForm)


class ModelForm(BaseModelForm):
    @classmethod
    def get_session(cls):
        return db.session


class PropertyForm(ModelForm):
    class Meta:
        csrf = False
        model = Extract

    id = HiddenField("")
    project_id = HiddenField("")
    delete = BooleanField("")
