from flask import abort, request
from flask_admin import Admin, expose
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from sqlalchemy import func

from src.models import Project, Resource, Url, db
from src.services.dao.project import ProjectDAO
from src.services.dao.resource import ResourceDAO
from src.views.mixins import LoginRequiredMixin

admin = Admin(name="[stlkr]", endpoint="my/", template_mode="bootstrap4")


class ProjectView(LoginRequiredMixin, ModelView):
    column_list = ["name"]
    form_columns = ("name",)

    def get_query(self):
        return self.session.query(self.model).where(
            self.model.user_id == current_user.id
        )

    def get_count_query(self):
        return self.session.query(func.count("*")).select_from(self.get_query())


class ResourceView(LoginRequiredMixin, ModelView):
    column_list = ["name"]
    form_columns = ("name",)

    @expose("/")
    def index_view(self):
        project_id = request.args.get("project", 0)
        dao = ProjectDAO(self.session)
        if (project := dao.get(project_id)) and project.user is current_user:
            return super().index_view()

        return abort(404)

    def get_query(self):
        return self.session.query(self.model).where(
            self.model.project_id == request.args.get("project")
        )

    def get_count_query(self):
        return self.session.query(func.count("*")).select_from(self.get_query())


class UrlView(LoginRequiredMixin, ModelView):
    column_list = ["address", "created_at", "published_at"]
    form_columns = ("address",)

    @expose("/")
    def index_view(self):
        resource_id = request.args.get("resource", 0)
        dao = ResourceDAO(self.session)
        if (resource := dao.get(resource_id)) and resource.project.user is current_user:
            return super().index_view()

        return abort(404)

    def get_query(self):
        return self.session.query(self.model).where(
            self.model.project_id == request.args.get("resource")
        )

    def get_count_query(self):
        return self.session.query(func.count("*")).select_from(self.get_query())


admin.add_view(ProjectView(Project, db.session))
admin.add_view(ResourceView(Resource, db.session))
admin.add_view(UrlView(Url, db.session))
