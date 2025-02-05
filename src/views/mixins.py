from abc import abstractmethod

from flask import flash, redirect, request, session, url_for
from flask_admin import expose
from flask_admin.base import AdminViewMeta
from flask_login import current_user
from sqlalchemy import func

from src.services.dao.page import PageDAO
from src.services.dao.project import ProjectDAO
from src.services.dao.resource import ResourceDAO
from src.services.dao.site import SiteDAO
from src.services.dao.url import UrlDAO


class LoginRequiredMixin:
    def is_accessible(self) -> bool:
        return current_user.is_active and super().is_accessible()

    def inaccessible_callback(self, name, **kwargs):
        if current_user.is_active:
            return redirect(url_for("projects.index_view"))

        flash("Войдите для доступа к странице.")

        return redirect(url_for("core.index_view", next=request.endpoint))


class UserAccessibleMixin:
    def get_query(self):
        return self.session.query(self.model).where(
            self.model.user_id == current_user.id
        )

    def get_count_query(self):
        return self.session.query(func.count("*")).select_from(self.get_query())


class AccessibleMixinMeta(metaclass=AdminViewMeta): ...


class AccessibleMixinInterface(AccessibleMixinMeta):
    def is_accessible(self) -> bool:
        # check url param on an index_view and session on create and edit views
        if id_ := self._get_arg_id():
            return self._is_model_accessible_by_user(id_) and super().is_accessible()

        return super().is_accessible()

    @abstractmethod
    def _is_model_accessible_by_user(self, model_id: int) -> bool: ...

    @abstractmethod
    def _get_arg_name(self) -> str: ...

    @abstractmethod
    def _get_redirect_endpoint(self) -> str: ...

    @expose("/")
    def index_view(self):
        if arg_id := request.args.get(self._get_arg_name(), type=int):
            # set session value from request arg to pass it to create/edit views
            session[self._get_arg_name()] = arg_id

            return super().index_view()

        return redirect(url_for(self._get_redirect_endpoint()))

    @staticmethod
    def is_visible():
        return False

    def get_query(self):
        return (
            super()
            .get_query()
            .where(
                getattr(self.model, self._get_model_attr_name())
                == request.args.get(self._get_arg_name(), -1, type=int)
            )
        )

    def _get_model_attr_name(self) -> str:
        return f"{self._get_arg_name()}_id"

    def get_count_query(self):
        return self.session.query(func.count("*")).select_from(self.get_query())

    def _get_arg_id(self) -> int | None:
        return (
            request.args.get(self._get_arg_name(), type=int)
            or session.get(self._get_arg_name())
            if not session.modified
            else None
        )


class ProjectAccessibleMixin(AccessibleMixinInterface):
    @staticmethod
    def _get_arg_name() -> str:
        return "project"

    @staticmethod
    def _get_redirect_endpoint() -> str:
        return "projects.index_view"

    def _is_model_accessible_by_user(self, project_id: int) -> bool:
        dao = ProjectDAO(self.session)
        return (project := dao.get(project_id)) and project.user_id == current_user.id


class ResourceAccessibleMixin(AccessibleMixinInterface):
    @staticmethod
    def _get_arg_name() -> str:
        return "resource"

    @staticmethod
    def _get_redirect_endpoint() -> str:
        return "resources.index_view"

    def _is_model_accessible_by_user(self, resource_id: int) -> bool:
        dao = ResourceDAO(self.session)
        return (
            resource := dao.get(resource_id)
        ) and resource.project.user_id == current_user.id


class SiteAccessibleMixin(AccessibleMixinInterface):
    @staticmethod
    def _get_arg_name() -> str:
        return "site"

    @staticmethod
    def _get_redirect_endpoint() -> str:
        return "sites.index_view"

    def _is_model_accessible_by_user(self, site_id: int) -> bool:
        dao = SiteDAO(self.session)
        return (site := dao.get(site_id)) and site.project.user_id == current_user.id


class PageAccessibleMixin(AccessibleMixinInterface):
    @staticmethod
    def _get_arg_name() -> str:
        # arg "page" is for pagination
        return "id"

    @staticmethod
    def _get_redirect_endpoint() -> str:
        return "sites.index_view"

    def _is_model_accessible_by_user(self, page_id: int) -> bool:
        dao = PageDAO(self.session)
        return (
            page := dao.get(page_id)
        ) and page.site.project.user_id == current_user.id

    def _get_model_attr_name(self) -> str:
        return "page_id"


class UrlAccessibleMixin(AccessibleMixinInterface):
    @staticmethod
    def _get_arg_name() -> str:
        return "url"

    @staticmethod
    def _get_redirect_endpoint() -> str:
        return "urls.index_view"

    def _is_model_accessible_by_user(self, site_id: int) -> bool:
        dao = UrlDAO(self.session)
        return (
            url := dao.get(site_id)
        ) and url.resource.project.user_id == current_user.id
