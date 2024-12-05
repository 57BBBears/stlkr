from flask import flash, redirect, request, session, url_for
from flask_admin import expose
from flask_login import current_user
from sqlalchemy import func

from src.services.dao.project import ProjectDAO


class LoginRequiredMixin:
    def is_accessible(self) -> bool:
        return current_user.is_active and super().is_accessible()

    def inaccessible_callback(self, name, **kwargs):
        if current_user.is_active:
            return redirect(url_for("projects.index_view"))

        flash("Войдите для доступа к странице.")

        return redirect(url_for("core.index_view", next=request.endpoint))


class ProjectAccessibleMixin:
    def is_accessible(self) -> bool:
        # check url param on a index_view and session on create and edit views
        if project_id := (
            request.args.get("project", type=int) or session.get("project")
            if not session.modified
            else None
        ):
            dao = ProjectDAO(self.session)
            return (
                (project := dao.get(project_id))
                and project.user_id == current_user.id
                and super().is_accessible()
            )

        return super().is_accessible()

    @expose("/")
    def index_view(self):
        if project_id := request.args.get("project", type=int):
            session["project"] = project_id

            return super().index_view()

        return redirect(url_for("projects.index_view"))

    def get_query(self):
        return (
            super()
            .get_query()
            .where(self.model.project_id == request.args.get("project", -1, type=int))
        )

    def get_count_query(self):
        return self.session.query(func.count("*")).select_from(self.get_query())
