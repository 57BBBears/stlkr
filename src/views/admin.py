import os

from flask import current_app, flash, redirect, request, session, url_for
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.actions import action
from flask_admin.contrib.sqla import ModelView
from flask_admin.menu import MenuLink
from flask_admin.model.template import EndpointLinkRowAction
from flask_admin.theme import Bootstrap4Theme
from flask_login import current_user
from sqlalchemy import func, select
from wtforms import HiddenField

from config import Config
from src.forms.page import LinkResourcesForm
from src.forms.resource import CopyPasteImportForm, CSVImportForm
from src.models import (
    Extract,
    Page,
    PageUrl,
    Project,
    Resource,
    ResourceExtract,
    Site,
    SiteExtract,
    Url,
    UrlExtract,
    db,
)
from src.services.admin.resource_view import (
    get_urls_from_csv,
    get_urls_from_text,
    open_temp_file,
    save_urls,
)
from src.services.admin.url_view import run_parse_urls_task
from src.services.dao.url import UrlDAO
from src.views.formatters import detail_url_formatter, page_urls_formatter
from src.views.mixins import (
    LoginRequiredMixin,
    PageAccessibleMixin,
    ProjectAccessibleMixin,
    ResourceAccessibleMixin,
    SiteAccessibleMixin,
    UrlAccessibleMixin,
)


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
            "fa fa-cog",
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
    column_filters = ("name",)
    column_list = ["name"]
    form_columns = ("project_id", "name")
    form_extra_fields = {
        "project_id": HiddenField("", render_kw={"readonly": True}),
    }
    list_template = "admin/custom_list.html"

    def create_form(self, obj=None):
        form = super().create_form(obj)
        form.project_id.data = session.get("project", None)

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
            "fa fa-cloud-download", ".import_urls_view", "Import urls"
        ),
        EndpointLinkRowAction(
            "fa fa-cog",
            "resource-extracts.index_view",
            "Extract settings",
            id_arg="resource",
        ),
    ]
    column_formatters = {"name": detail_url_formatter("urls.index_view", "resource")}
    list_template = "admin/custom_list.html"

    def create_form(self, obj=None):
        form = super().create_form(obj)
        form.project_id.data = session.get("project", None)

        return form

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
                    f"{current_user.id}_{self._get_arg_id()}.csv",
                )
                with open_temp_file(file_path, csv_form.file.data) as file:
                    urls, not_urls = get_urls_from_csv(
                        file,
                        csv_form.delimiter.data if csv_form.delimiter.data else ",",
                    )

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
        inserted_url = save_urls(urls, self._get_model_id(), dao)
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
        resource_id = str(self._get_model_id())
        return (
            resource := self.get_one(resource_id)
        ) and resource.project.user_id == current_user.id

    @staticmethod
    def _get_model_id() -> int:
        return request.args.get("id", -1, type=int)


class ResourceExtractView(LoginRequiredMixin, ResourceAccessibleMixin, ModelView):
    column_list = ["resource", "extract", "selector"]
    form_columns = ("resource_id", "extract", "selector")
    list_template = "admin/custom_list.html"
    form_extra_fields = {"resource_id": HiddenField("", render_kw={"readonly": True})}

    def create_form(self, obj=None):
        form = super().create_form(obj)
        form.resource_id.data = session.get("resource")
        return form


class UrlView(LoginRequiredMixin, ResourceAccessibleMixin, ModelView):
    column_filters = ("address",)
    column_list = ["address", "created_at", "published_at"]
    form_columns = ("resource_id", "address")
    column_formatters = {
        "address": detail_url_formatter("url-extracts.index_view", "url")
    }
    form_extra_fields = {
        "resource_id": HiddenField("", render_kw={"readonly": True}),
    }
    list_template = "admin/custom_list.html"

    def create_form(self, obj=None):
        form = super().create_form(obj)
        form.resource_id.data = session.get("resource")

        return form

    @action("Parse", "Parse urls", "Are you sure you want to parse selected urls?")
    def action_parse(self, ids):
        run_parse_urls_task(
            current_user.id, int(request.args["resource"]), ids, self.session
        )
        flash(f"Task parsing {len(ids)} urls has been launched.")


class UrlExtractView(LoginRequiredMixin, UrlAccessibleMixin, ModelView):
    column_list = [
        "url",
        "extract",
        "draft",
        "data",
        "draft_modified_at",
        "data_modified_at",
    ]
    form_columns = ("url_id", "extract", "draft", "data")
    form_extra_fields = {
        "url_id": HiddenField("", render_kw={"readonly": True}),
    }
    list_template = "admin/custom_list.html"

    @property
    def form_args(self):
        return {
            "extract": {
                "query_factory": lambda: Extract.query.filter(
                    Extract.project_id
                    == select(Resource.project_id)
                    .join(Url)
                    .where(Url.id == session.get("url"))
                    .scalar_subquery()
                )
            }
        }

    def create_form(self, obj=None):
        form = super().create_form(obj)
        form.url_id.data = session.get("url")

        return form


class SiteView(LoginRequiredMixin, ModelView):
    column_filters = ("project", "name", "domain")
    column_list = ["project", "name", "domain"]
    form_columns = ("project", "name", "domain", "index_page", "template")

    @property
    def form_args(self):
        return {
            "project": {"query_factory": lambda: reversed(current_user.projects)},
            "index_page": {
                "query_factory": lambda: Page.query.filter(
                    Page.site_id == request.args.get("id")
                )
            },
        }

    # inline_models = [(Project, dict(form_columns=['name']))]
    column_formatters = {"name": detail_url_formatter("pages.index_view", "site")}
    list_template = "admin/custom_list.html"
    column_extra_row_actions = [
        EndpointLinkRowAction(
            "fa fa-cog",
            "site-extracts.index_view",
            "Extract settings",
            "site",
        )
    ]

    def get_query(self):
        return (
            super().get_query().join(Project).where(Project.user_id == current_user.id)
        )

    def get_count_query(self):
        return self.session.query(func.count("*")).select_from(self.get_query())


class SiteExtractView(LoginRequiredMixin, SiteAccessibleMixin, ModelView):
    column_list = ["site", "extract", "code", "is_preview"]
    form_columns = ("site_id", "extract", "code", "is_preview")
    list_template = "admin/custom_list.html"
    form_extra_fields = {"site_id": HiddenField("", render_kw={"readonly": True})}

    @property
    def form_args(self):
        return {
            "extract": {
                "query_factory": lambda: Extract.query.filter(
                    Extract.project_id
                    == select(Site.project_id)
                    .where(Site.id == session.get("site"))
                    .scalar_subquery()
                )
            }
        }

    def create_form(self, obj=None):
        form = super().create_form(obj)
        form.site_id.data = session.get("site")
        return form


class PageView(LoginRequiredMixin, SiteAccessibleMixin, ModelView):
    column_filters = ("site", "name", "slug")
    column_list = ["site", "name", "slug"]
    form_columns = (
        "site_id",
        "parent",
        "name",
        "slug",
        "title",
        "description",
        "keywords",
        "heading",
        "excerpt",
        "content",
        "image",
        "template",
    )
    column_formatters = {"name": page_urls_formatter("page-urls.index_view", "id")}
    form_extra_fields = {
        "site_id": HiddenField("", render_kw={"readonly": True}),
    }
    list_template = "admin/custom_list.html"
    column_extra_row_actions = [
        EndpointLinkRowAction(
            "fa fa-link",
            ".link_resources_view",
            "Link resources to the page",
        ),
    ]

    @property
    def form_args(self):
        return {
            "parent": {
                "query_factory": lambda: Page.query.filter(
                    Page.site_id == session.get("site"),
                    Page.id != request.args.get("id", -1, type=int),
                )
            }
        }

    def create_form(self, obj=None):
        form = super().create_form(obj)
        form.site_id.data = session.get("site")

        return form

    @expose("/link/", methods=("GET", "POST"))
    def link_resources_view(self):
        if self._is_page_accessible():
            form = LinkResourcesForm()

            if form.validate_on_submit():
                page = self.get_one(self._get_model_id())
                page.urls = [
                    url for resource in form.resources.data for url in resource.urls
                ]
                self.session.commit()
                flash("Resources has been successfully linked.", "success")

                return redirect(url_for(".index_view", site=session.get("site")))

            return self.render(
                "admin/link_resources.html", title="Link resources", form=form
            )

        return redirect(url_for(".index_view", site=session.get("site")))

    def _is_page_accessible(self):
        page_id = self._get_model_id()
        return (
            page := self.get_one(page_id)
        ) and page.site.project.user_id == current_user.id

    @staticmethod
    def _get_model_id() -> str:
        return request.args.get("id", "-1", type=str)


class PageUrlView(LoginRequiredMixin, PageAccessibleMixin, ModelView):
    can_create = False
    can_edit = False
    column_list = ["page", "url", "created_at"]
    list_template = "admin/custom_list.html"


admin = Admin(
    name="[stlkr]",
    url="/my/",
    index_view=AdminView(),
    theme=Bootstrap4Theme(swatch="cerulean"),
    host=Config.CORE_DOMAIN,
)
admin.add_view(ProjectView(Project, db.session, "Проекты", endpoint="projects"))
admin.add_view(
    ExtractView(
        Extract, db.session, "Настройки извлекаемых данных", endpoint="extracts"
    )
)
admin.add_view(
    ResourceExtractView(
        ResourceExtract,
        db.session,
        "Настройки извлекаемых данных",
        endpoint="resource-extracts",
    )
)
admin.add_view(ResourceView(Resource, db.session, "Ресурсы", endpoint="resources"))
admin.add_view(UrlView(Url, db.session, "Ссылки", endpoint="urls"))
admin.add_view(
    UrlExtractView(
        UrlExtract, db.session, "Извлечённые данные", endpoint="url-extracts"
    )
)
admin.add_view(SiteView(Site, db.session, "Сайты", endpoint="sites"))
admin.add_view(
    SiteExtractView(
        SiteExtract,
        db.session,
        "Настройки извлекаемых данных",
        endpoint="site-extracts",
    )
)
admin.add_view(PageView(Page, db.session, "Страницы", endpoint="pages"))
admin.add_view(
    PageUrlView(PageUrl, db.session, "Привязанные ссылки", endpoint="page-urls")
)

admin.add_link(MenuLink(name="Выйти", endpoint="core.logout_view"))
