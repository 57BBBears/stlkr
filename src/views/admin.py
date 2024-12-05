import os

from flask import current_app, flash, redirect, request, session, url_for
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.menu import MenuLink
from flask_admin.model.template import EndpointLinkRowAction
from flask_login import current_user
from sqlalchemy import func
from wtforms import HiddenField

from src.forms.resource import CopyPasteImportForm, CSVImportForm
from src.models import Extract, Project, Resource, Url, db
from src.services.admin.resource_view import (
    get_urls_from_csv,
    get_urls_from_text,
    open_temp_file,
    save_urls,
)
from src.services.dao.resource import ResourceDAO
from src.services.dao.url import UrlDAO
from src.views.formatters import detail_url_formatter
from src.views.mixins import LoginRequiredMixin, ProjectAccessibleMixin


class AdminView(LoginRequiredMixin, AdminIndexView):
    # def __init__(self, session, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self.session = session

    def is_visible(self):
        # This view won't appear in the menu structure
        return False


class ProjectView(LoginRequiredMixin, ModelView):
    column_filters = ("name",)
    column_list = ["name"]
    form_columns = (
        "user_id",
        "name",
    )
    form_extra_fields = {
        "user_id": HiddenField("", render_kw={"readonly": True}),
    }
    column_formatters = {
        "name": detail_url_formatter("resources.index_view", "project")
    }
    list_template = "admin/custom_list.html"
    column_extra_row_actions = [
        EndpointLinkRowAction(
            "glyphicon glyphicon-cog",
            "extracts.index_view",
            "Extract settings",
            "project",
        )
    ]

    def create_form(self, obj=None):
        form = super().create_form(obj)
        form.user_id.data = current_user.id

        return form

    def get_query(self):
        return self.session.query(self.model).where(
            self.model.user_id == current_user.id
        )

    def get_count_query(self):
        return self.session.query(func.count("*")).select_from(self.get_query())


class ExtractView(LoginRequiredMixin, ProjectAccessibleMixin, ModelView):
    column_filters = ("name", "code")
    column_list = ["name", "code"]
    form_columns = ("project_id", "name", "code")
    form_extra_fields = {
        "project_id": HiddenField("", render_kw={"readonly": True}),
    }
    list_template = "admin/custom_list.html"

    def is_visible(self):
        return False

    def create_form(self, obj=None):
        form = super().create_form(obj)
        form.project_id.data = current_user.id

        return form


class ResourceView(LoginRequiredMixin, ProjectAccessibleMixin, ModelView):
    column_filters = ("name",)
    column_list = ["name"]
    form_columns = (
        "project_id",
        "name",
    )
    form_extra_fields = {
        "project_id": HiddenField("", render_kw={"readonly": True}),
    }
    column_extra_row_actions = [
        EndpointLinkRowAction(
            "glyphicon glyphicon-cloud-download", ".import_urls_view", "Import urls"
        )
    ]
    column_formatters = {"name": detail_url_formatter("urls.index_view", "resource")}
    list_template = "admin/custom_list.html"

    def create_form(self, obj=None):
        form = super().create_form(obj)
        form.project_id.data = session.get("project", None)

        return form

    def is_visible(self):
        return False

    @expose("/import/", methods=("GET", "POST"))
    def import_urls_view(self):
        if self._is_resource_accessible():
            copy_paste_form = CopyPasteImportForm()
            csv_form = CSVImportForm(current_app.config["MAX_IMPORT_FILE_SIZE_KB"])

            if copy_paste_form.copy_paste.data and copy_paste_form.validate_on_submit():
                urls, not_urls = get_urls_from_text(
                    copy_paste_form.urls.data,
                    copy_paste_form.delimiter.data
                    if copy_paste_form.delimiter.data
                    else "\r\n",
                )

                return self._save_urls(urls, not_urls)

            if csv_form.csv.data and csv_form.validate_on_submit():
                file_path = os.path.join(
                    current_app.instance_path,
                    "import",
                    f"{current_user.id}_{self.resource_id}.csv",
                )
                with open_temp_file(file_path, csv_form.file.data) as file:
                    urls, not_urls = get_urls_from_csv(
                        file,
                        csv_form.delimiter.data if csv_form.delimiter.data else ",",
                    )
                print(urls, not_urls)
                return self._save_urls(urls, not_urls)

            return self.render(
                "admin/import_urls.html",
                title="Импорт",
                copy_paste_form=copy_paste_form,
                csv_form=csv_form,
            )

        return redirect(url_for(".index_view", project=session.get("project")))

    def _save_urls(self, urls: set[str], not_urls: list[str]):
        dao = UrlDAO(self.session)
        inserted_url = save_urls(urls, self.resource_id, dao)
        dao.commit()
        flash(
            f"Всего: {len(urls) + len(not_urls)} "
            f"Добавлено: {len(inserted_url)} "
            f"Дублей: {len(urls) - len(inserted_url)} "
            f"Ошибок: {len(not_urls)}",
            "info",
        )

        if not_urls:
            flash(f"Ошибки: {", ".join(not_urls)}", "warning")

        return redirect(url_for(request.endpoint, **request.args))

    def _is_resource_accessible(self):
        resource_id = request.args.get("id", -1, type=int)
        dao = ResourceDAO(self.session)
        return (
            resource := dao.get(resource_id)
        ) and resource.project.user_id == current_user.id


class UrlView(LoginRequiredMixin, ModelView):
    column_filters = ("address",)
    column_list = ["address", "created_at", "published_at"]
    form_columns = (
        "resource_id",
        "address",
    )
    form_extra_fields = {
        "resource_id": HiddenField("", render_kw={"readonly": True}),
    }
    list_template = "admin/custom_list.html"

    def create_form(self, obj=None):
        form = super().create_form(obj)
        form.resource_id.data = session.get("resource", None)

        return form

    def is_visible(self):
        return False

    @expose("/")
    def index_view(self):
        if self._is_resource_accessible():
            session["resource"] = request.args["resource"]
            return super().index_view()

        return redirect(url_for("resources.index_view"))

    def get_query(self):
        return self.session.query(self.model).where(
            self.model.resource_id == request.args.get("resource", -1)
        )

    def get_count_query(self):
        return self.session.query(func.count("*")).select_from(self.get_query())

    def _is_resource_accessible(self):
        resource_id = request.args.get("resource") or -1
        dao = ResourceDAO(self.session)
        return (
            resource := dao.get(resource_id)
        ) and resource.project.user_id == current_user.id


admin = Admin(
    name="[stlkr]", url="/my/", index_view=AdminView(), template_mode="bootstrap3"
)
admin.add_view(ProjectView(Project, db.session, "Проекты", endpoint="projects"))
admin.add_view(
    ExtractView(
        Extract, db.session, "Настройки извлекаемых данных", endpoint="extracts"
    )
)
admin.add_view(ResourceView(Resource, db.session, "Ресурсы", endpoint="resources"))
admin.add_view(UrlView(Url, db.session, "Ссылки", endpoint="urls"))

admin.add_link(MenuLink(name="Выйти", endpoint="core.logout_view"))
