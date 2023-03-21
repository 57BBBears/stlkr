from flask import render_template, abort
from sqlalchemy.exc import NoResultFound, MultipleResultsFound
from app import db
from app.pages import bp
from app.core.models import Url, Check, UrlCheck, DataFrame, Cluster, DataFrameCluster

@bp.route('/')
def index():
    return render_template('pages/index.html')

@bp.route('/catalog/<slug>/')
def category(slug):
    cluster = Cluster.query.filter_by(slug=slug).first_or_404()

    cluster_active_checks = db.session.query(DataFrame.check_id).join(DataFrameCluster).filter(
        DataFrameCluster.c.cluster_id==cluster.id,
        DataFrame.check_id.isnot(None)
    )

    data = db.session.query(UrlCheck.url_id, UrlCheck.extracted_data).where(
        UrlCheck.check_id.in_(cluster_active_checks),
        UrlCheck.extracted_data.isnot(None)
    )
    
    data = data.all()

    return render_template('pages/store.html', data=data)

@bp.route('/catalog/<pk>.html')
def detail(pk):
    active_check = db.session.query(Check.id).join(
        DataFrame, DataFrame.check_id==Check.id
    ).where(DataFrame.id==Url.dataframe_id, Url.id==pk)

    url_data = db.session.query(UrlCheck).where(
        UrlCheck.url_id==pk,
        UrlCheck.check_id==active_check,
        UrlCheck.extracted_data.isnot(None)
    )

    try:
        url_data = url_data.one()
    except (NoResultFound, MultipleResultsFound):
        abort(404)

    return render_template('pages/product.html', url_data=url_data)
