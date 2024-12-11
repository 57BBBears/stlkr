from flask import request
from flask_wtf import FlaskForm
from sqlalchemy import select
from wtforms import SubmitField
from wtforms_alchemy import QuerySelectMultipleField

from src.models import Page, Project, Resource, Site


class LinkResourcesForm(FlaskForm):
    resources = QuerySelectMultipleField(
        "Resources",
        query_factory=lambda: Resource.query.filter(
            Resource.project_id
            == select(Project.id)
            .join(Site)
            .where(
                Page.site_id == Site.id, Page.id == request.args.get("id", -1, type=int)
            )
            .scalar_subquery()
        ),
    )

    submit = SubmitField("Link")
