import datetime
from typing import Annotated, Any, Optional

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from furl import furl
from sqlalchemy import (
    DateTime,
    ForeignKey,
    MetaData,
    String,
    UniqueConstraint,
    event,
    false,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    declarative_base,
    mapped_column,
    relationship,
)
from sqlalchemy.sql import true
from sqlalchemy_utils import (
    EmailType,
    JSONType,
    PasswordType,
    URLType,
    force_auto_coercion,
)

POSTGRES_INDEXES_NAMING_CONVENTION = {
    "ix": "%(column_0_label)s_idx",
    "uq": "%(table_name)s_%(column_0_name)s_key",
    "ck": "%(table_name)s_%(constraint_name)s_check",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "%(table_name)s_pkey",
}
metadata = MetaData(naming_convention=POSTGRES_INDEXES_NAMING_CONVENTION)


class Base: ...


Base = declarative_base(cls=Base, metadata=metadata)

db = SQLAlchemy(model_class=Base)

force_auto_coercion()

timestamp = Annotated[
    datetime.datetime,
    mapped_column(DateTime(timezone=True), server_default=func.current_timestamp()),
]


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(EmailType, unique=True)
    password: Mapped[str] = mapped_column(
        PasswordType(
            max_length=255, schemes=["scrypt", "md5_crypt"], deprecated=["md5_crypt"]
        )
    )
    is_verified: Mapped[bool] = mapped_column(server_default=false())

    projects: Mapped[list["Project"]] = relationship(
        back_populates="user", passive_deletes=True
    )

    def is_correct_password(self, plaintext: str):
        return self.password == plaintext


# @event.listens_for(User.password, "set", retval=True)
# def hash_password(target, value, oldvalue, initiator):
#     return generate_password_hash(value)


class Project(db.Model):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey(User.id, ondelete="cascade"))
    name: Mapped[str] = mapped_column(String(255))

    user: Mapped[User] = relationship(back_populates="projects")
    resources: Mapped[list["Resource"]] = relationship(
        back_populates="project", passive_deletes=True
    )
    extracts: Mapped[list["Extract"]] = relationship(
        back_populates="project", passive_deletes=True
    )
    sites: Mapped[list["Site"]] = relationship(
        back_populates="project", passive_deletes=True
    )

    def __str__(self):
        return self.name


class Resource(db.Model):
    """Resource of data contains urls."""

    __tablename__ = "resources"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey(Project.id, ondelete="cascade"))
    name: Mapped[str] = mapped_column(String(255))

    project: Mapped[Project] = relationship(back_populates="resources")
    urls: Mapped[list["Url"]] = relationship(
        back_populates="resource", passive_deletes=True
    )
    selectors: Mapped[list["ResourceExtract"]] = relationship(
        back_populates="resource", passive_deletes=True
    )

    # @column_property
    # def url_count(self):
    #     return (
    #         select(func.count(Url.id)).where(self.id == Url.resource_id)
    #     )

    def __str__(self):
        return self.name


class Url(db.Model):
    """Urls to get data from."""

    __tablename__ = "urls"

    id: Mapped[int] = mapped_column(primary_key=True)
    resource_id: Mapped[int] = mapped_column(
        ForeignKey(Resource.id, ondelete="cascade")
    )
    address: Mapped[furl] = mapped_column(URLType())
    created_at: Mapped[timestamp]
    published_at: Mapped[datetime.datetime | None]

    resource_id_address_key = UniqueConstraint(
        resource_id, address, name="urls_resource_id_address_key"
    )

    resource: Mapped[Resource] = relationship(back_populates="urls")
    pages: Mapped[list["Page"]] = relationship(
        back_populates="urls", secondary="pages_urls", passive_deletes=True
    )
    url_pages: Mapped[list["PageUrl"]] = relationship(
        back_populates="url", viewonly=True
    )

    def __str__(self):
        return str(self.address)

    # @validates("address")
    # def validate_url(self, key, url):
    #     if not validators.url(url):
    #         raise ValueError(f"{url} is not url.")
    #
    #     return url


class Extract(db.Model):
    """Project settings for extracting data."""

    __tablename__ = "extracts"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey(Project.id, ondelete="cascade"))
    name: Mapped[str] = mapped_column(String(255))

    project: Mapped[Project] = relationship(back_populates="extracts")
    sites: Mapped[list["Site"]] = relationship(
        back_populates="extracts", secondary="sites_extracts", passive_deletes=True
    )
    pages: Mapped[list["Page"]] = relationship(
        back_populates="extracts", secondary="pages_extracts", passive_deletes=True
    )
    selectors: Mapped[list["ResourceExtract"]] = relationship(
        back_populates="extract", passive_deletes=True
    )
    site_extracts: Mapped[list["SiteExtract"]] = relationship(
        back_populates="extract", viewonly=True
    )

    def __repr__(self):
        return self.name


class ResourceExtract(db.Model):
    """Many to many table."""

    __tablename__ = "resources_extracts"

    id: Mapped[int] = mapped_column(primary_key=True)
    resource_id: Mapped[int] = mapped_column(
        ForeignKey(Resource.id, ondelete="cascade")
    )
    extract_id: Mapped[int] = mapped_column(ForeignKey(Extract.id, ondelete="cascade"))
    selector: Mapped[str] = mapped_column(String(255), info={"label": "xpath"})

    UniqueConstraint(
        resource_id,
        extract_id,
        name="resources_extracts_resource_id_extract_id_key",
    )

    resource: Mapped[Resource] = relationship(back_populates="selectors")
    extract: Mapped[Extract] = relationship(back_populates="selectors")


class UrlExtract(db.Model):
    """Many to many table."""

    __tablename__ = "urls_extracts"

    id: Mapped[int] = mapped_column(primary_key=True)
    url_id: Mapped[int] = mapped_column(ForeignKey(Url.id, ondelete="cascade"))
    extract_id: Mapped[int] = mapped_column(ForeignKey(Extract.id, ondelete="cascade"))
    draft: Mapped[str] = mapped_column(server_default="")
    data: Mapped[str] = mapped_column(server_default="")
    draft_modified_at: Mapped[datetime.datetime | None]
    data_modified_at: Mapped[datetime.datetime | None]

    UniqueConstraint(url_id, extract_id, name="urls_extracts_url_id_extract_id_key")

    @staticmethod
    def set_data_modified(target, value, oldvalue, initiator):
        target.data_modified_at = datetime.datetime.now(datetime.UTC)

    @staticmethod
    def set_draft_modified(target, value, oldvalue, initiator):
        target.draft_modified_at = datetime.datetime.now(datetime.UTC)


event.listen(UrlExtract.data, "set", UrlExtract.set_data_modified, retval=False)
event.listen(UrlExtract.draft, "set", UrlExtract.set_draft_modified, retval=False)


class Site(db.Model):
    __tablename__ = "sites"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey(Project.id, ondelete="cascade"))
    name: Mapped[str] = mapped_column(String(255))
    domain: Mapped[str] = mapped_column(unique=True)
    options: Mapped[dict[str, Any]] = mapped_column(JSONType(), server_default="{}")
    index_page_id: Mapped[int | None] = mapped_column(
        ForeignKey("pages.id", ondelete="SET NULL")
    )

    project: Mapped[Project] = relationship(back_populates="sites")
    pages: Mapped[list["Page"]] = relationship(
        back_populates="site", foreign_keys="Page.site_id", passive_deletes=True
    )
    index_page: Mapped["Page"] = relationship(
        back_populates="index_site", foreign_keys=[index_page_id]
    )
    extracts: Mapped[list[Extract]] = relationship(
        back_populates="sites", secondary="sites_extracts", passive_deletes=True
    )
    site_extracts: Mapped[list["SiteExtract"]] = relationship(
        back_populates="site", viewonly=True
    )

    def __str__(self):
        return self.name


class SiteExtract(db.Model):
    """Many to many table. Set code for extracts."""

    __tablename__ = "sites_extracts"

    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey(Site.id, ondelete="cascade"))
    extract_id: Mapped[int] = mapped_column(ForeignKey(Extract.id, ondelete="cascade"))
    code: Mapped[str] = mapped_column(String(255))
    is_preview: Mapped[bool] = mapped_column(server_default=true())

    UniqueConstraint(site_id, extract_id, name="sites_extracts_site_id_extract_id_key")

    site: Mapped[Site] = relationship(back_populates="site_extracts", viewonly=True)
    extract: Mapped[Extract] = relationship(
        back_populates="site_extracts", viewonly=True
    )


class Page(db.Model):
    __tablename__ = "pages"

    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey(Site.id, ondelete="cascade"))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey(id, ondelete="cascade"))
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(255), server_default="")
    description: Mapped[str] = mapped_column(String(255), server_default="")
    keywords: Mapped[str] = mapped_column(String(255), server_default="")
    heading: Mapped[str] = mapped_column(String(255), server_default="")
    excerpt: Mapped[str] = mapped_column(server_default="")
    content: Mapped[str] = mapped_column(server_default="")
    image: Mapped[str] = mapped_column(String(255), server_default="")
    template: Mapped[str] = mapped_column(String(255), server_default="")
    created_at: Mapped[timestamp]
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        server_onupdate=func.current_timestamp(),
    )

    UniqueConstraint(site_id, name, name="sections_site_id_name_key")
    UniqueConstraint(site_id, slug, name="sections_site_id_slug_key")

    site: Mapped[Site] = relationship(back_populates="pages", foreign_keys=[site_id])
    index_site: Mapped[Site | None] = relationship(
        back_populates="index_page",
        foreign_keys=[Site.index_page_id],
        passive_deletes=True,
    )
    parent: Mapped[Optional["Page"]] = relationship(
        back_populates="children", remote_side=[id], passive_deletes=True
    )
    children: Mapped[list["Page"]] = relationship(
        back_populates="parent", remote_side=[parent_id]
    )
    extracts: Mapped[list[Extract]] = relationship(
        back_populates="pages", secondary="pages_extracts"
    )
    urls: Mapped[list[Url]] = relationship(
        back_populates="pages", secondary="pages_urls", passive_deletes=True
    )
    page_urls: Mapped[list["PageUrl"]] = relationship(
        back_populates="page", viewonly=True
    )

    def __str__(self):
        return self.name


class PageExtract(db.Model):
    """Many to many table."""

    __tablename__ = "pages_extracts"

    id: Mapped[int] = mapped_column(primary_key=True)
    page_id: Mapped[int] = mapped_column(ForeignKey(Page.id, ondelete="cascade"))
    extract_id: Mapped[int] = mapped_column(ForeignKey(Extract.id, ondelete="cascade"))

    UniqueConstraint(page_id, extract_id, name="pages_extracts_page_id_extract_id_key")


class PageUrl(db.Model):
    """Many to many table."""

    __tablename__ = "pages_urls"

    id: Mapped[int] = mapped_column(primary_key=True)
    page_id: Mapped[int] = mapped_column(ForeignKey(Page.id, ondelete="cascade"))
    url_id: Mapped[int] = mapped_column(ForeignKey(Url.id, ondelete="cascade"))
    created_at: Mapped[timestamp]

    UniqueConstraint(page_id, url_id, name="pages_urls_page_id_url_id_key")

    page: Mapped[Page] = relationship(back_populates="page_urls", viewonly=True)
    url: Mapped[Url] = relationship(back_populates="url_pages", viewonly=True)
