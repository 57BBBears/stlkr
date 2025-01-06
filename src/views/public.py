# from src.models import (
#     Check,
#     Cluster,
#     Resource,
#     DataframeCluster,
#     Property,
#     Url,
#     UrlProperty,
# )
from functools import partial

from flask import Blueprint, abort, current_app, render_template, send_from_directory
from werkzeug.security import safe_join

from src.models import db
from src.services.dao.page import PageDAO
from src.services.dao.site import SiteDAO

bp = Blueprint("public", __name__)
route = partial(bp.route, host="<host>")


@route("/")
def index_view(host: str):
    dao = SiteDAO(db.session)
    if site := dao.get_by_domain(host):
        template, context = site.index_page.get_render_template()
        return render_template(template, **context)

    abort(404)


@route("/<path:filename>.<string:extension>")
def static_view(host: str, filename: str, extension: str):
    dao = SiteDAO(db.session)
    if site := dao.get_by_domain(host):
        return send_from_directory(
            safe_join(
                current_app.config["PUBLIC_TEMPLATE_FOLDER"], site.get_template_folder()
            ),
            f"{filename}.{extension}",
        )

    abort(404)


@route("/<path:slug>/")
def page_view(host: str, slug: str):
    dao = PageDAO(db.session)
    if page := dao.get_by_slug(host, slug):
        template, context = page.get_render_template()
        return render_template(template, **context)

    abort(404)


# @bp.route("/catalog/<slug>/")
# def category(slug):
#     cluster = Cluster.query.filter_by(slug=slug).first_or_404()
#
#     # select all active checks of the dataframes of the cluster
#     cluster_active_checks = (
#         db.session.query(Resource.check_id.label("check_id"))
#         .join(DataframeCluster)
#         .where(
#             DataframeCluster.c.cluster_id == cluster.id, Resource.check_id.isnot(None)
#         )
#         .subquery()
#     )
#
#     # select properties that are used in dataframes of the cluster
#     cluster_properties = (
#         db.session.query(UrlProperty.property_id, Property.code)
#         .distinct(UrlProperty.property_id)
#         .join(
#             cluster_active_checks,
#             UrlProperty.check_id == cluster_active_checks.c.check_id,
#         )
#         .join(Property)
#     )
#
#     # all urls of the cluster
#     cluster_urls = (
#         db.session.query(UrlProperty.url_id.label("id"))
#         .distinct()
#         .join(
#             cluster_active_checks,
#             cluster_active_checks.c.check_id == UrlProperty.check_id,
#         )
#         .subquery()
#     )
#
#     urls_properties = db.session.query(cluster_urls)
#     # join properties to urls
#     for prop_id, code in cluster_properties:
#         subquery = (
#             db.session.query(UrlProperty.url_id.label("url_id"), UrlProperty.data)
#             .join(
#                 cluster_active_checks,
#                 cluster_active_checks.c.check_id == UrlProperty.check_id,
#             )
#             .where(UrlProperty.property_id == prop_id)
#             .subquery(code)
#         )
#
#         urls_properties = urls_properties.outerjoin(
#             subquery, cluster_urls.c.id == subquery.c.url_id
#         ).add_columns(subquery.c.data.label(code))
#
#     # TODO compare speed of sql  join + filter vs join filtered
#     """
#     cluster_urls = db.session.query(UrlProperty.url_id.label('url_id'),
#     UrlProperty.check_id.label('check_id')).distinct().join(cluster_active_checks,
#     cluster_active_checks.c.check_id==UrlProperty.check_id).subquery()
#     prop_titles = db.session.query(UrlProperty.url_id.label('url_id'),
#     UrlProperty.check_id.label('check_id'), UrlProperty.data).where(
#     UrlProperty.property_id==3).subquery()
#     prop_decrs = db.session.query(UrlProperty.url_id.label('url_id'),
#     UrlProperty.check_id.label('check_id'), UrlProperty.data).where(
#     UrlProperty.property_id==6).subquery()
#     urls_properties = db.session.query(cluster_urls.c.url_id, prop_titles.c.data,
#     prop_decrs.c.data).outerjoin(
#         prop_titles, and_(cluster_urls.c.url_id==prop_titles.c.url_id,
#         cluster_urls.c.check_id==prop_titles.c.check_id)
#     ).outerjoin(
#         prop_decrs, and_(cluster_urls.c.url_id == prop_decrs.c.url_id,
#         cluster_urls.c.check_id==prop_decrs.c.check_id)
#     )
#     """
#     per_page = request.args.get(
#         "per_page", current_app.config["URLS_PER_PAGE"], type=int
#     )
#     urls = urls_properties.paginate(per_page=per_page)
#     return render_template("pages/store.html", urls=urls.items)
#
#
# @bp.route("/catalog/<pk>.html")
# def detail(pk):
#     active_check = (
#         db.session.query(Check.id)
#         .join(Resource, Resource.check_id == Check.id)
#         .where(Resource.id == Url.dataframe_id, Url.id == pk)
#         .limit(1)
#         .scalar_subquery()
#     )
#
#     url_stmt = (
#         db.session.query(Property.code, UrlProperty.data)
#         .join(UrlProperty)
#         .where(UrlProperty.url_id == pk, UrlProperty.check_id == active_check)
#     )
#
#     if url_data := url_stmt.all():
#         url = {name: data for name, data in url_data}
#     else:
#         abort(404)
#
#     return render_template("pages/product.html", url=url)
