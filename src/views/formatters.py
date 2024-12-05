from flask import url_for
from markupsafe import Markup


def detail_url_formatter(endpoint: str, param_name: str):
    def formatter(view, context, model, name):
        return Markup(
            f"<a href='{url_for(endpoint, **{param_name: model.id})}'>"
            f"{model.name}</a>"
        )

    return formatter
