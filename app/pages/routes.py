from flask import render_template
from app.models import Cluster
from app.pages import bp

@bp.route('/')
def index():
    return render_template('pages/index.html')
@bp.route('/catalog/<slug>/')
def category(slug):
    ...

@bp.route('/catalog/<pk>/')
def detail(pk):
    ...