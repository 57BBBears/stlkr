from flask_wtf import FlaskForm
from wtforms_alchemy import model_form_factory

from src.models import db

BaseModelForm = model_form_factory(FlaskForm)


class ModelForm(BaseModelForm):
    @classmethod
    def get_session(cls):
        return db.session
