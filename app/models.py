import validators
from flask import current_app
from app import db
from sqlalchemy.orm import validates
from sqlalchemy_utils import URLType
from datetime import datetime


class DataFrame(db.Model):
    __tablename__ = 'dataframe'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, info={'label': 'Название'})
    description = db.Column(db.String(150), info={'label': 'Описание'})

    urls = db.relationship('Url', back_populates='dataframe', lazy='select', cascade='all, delete-orphan')
    checks = db.relationship('Check',
                             order_by='desc(Check.id)',
                             back_populates='dataframe',
                             lazy='select',
                             cascade='all, delete-orphan')

    @property
    def url_count(self):
        return Url.query.filter_by(dataframe=self).count()

    #  clusters = db.relationship('Cluster', secondary='DataFrameCluster', backref='dataframes', lazy='select')


class Url(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dataframe_id = db.Column(db.Integer, db.ForeignKey(DataFrame.id, ondelete='cascade'), nullable=False)
    url = db.Column(URLType(500))

    checks = db.relationship('UrlCheck', back_populates='url', lazy='select', cascade='all, delete-orphan')
    dataframe = db.relationship(DataFrame, back_populates='urls', lazy='select')

    @validates('url')
    def validate_url(self, key, url):
        if not validators.url(url):
            raise ValueError(f'{url} failed url validation.')

        return url
    # TODO add url dataframe_id unique constraint to avoid duplicates


class Check(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dataframe_id = db.Column(db.Integer, db.ForeignKey(DataFrame.id, ondelete='cascade'), nullable=False)
    name = db.Column(db.String(50), nullable=False, info={'label': 'Название'})
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime)
    # TODO add task_id to find and stop check task in the future by id ?

    urls = db.relationship('UrlCheck', back_populates='check', lazy='select', cascade='all, delete-orphan')
    dataframe = db.relationship(DataFrame, back_populates='checks', lazy='select')

    def start(self, priority='default', **kwargs):
        queue = current_app.queue.get(priority, 'default')
        task = queue.enqueue('app.tasks.check_dataframe', self.id, **kwargs)
        current_app.logger.info(f'Task "check_dataframe" has launched. Task id: {task.get_id()}')

    def stop(self):
        pass


class UrlCheck(db.Model):
    url_id = db.Column(db.Integer, db.ForeignKey(Url.id, ondelete='cascade'), primary_key=True)
    check_id = db.Column(db.Integer, db.ForeignKey(Check.id, ondelete='cascade'), primary_key=True)
    status = db.Column(db.Integer)
    data = db.Column(db.Text)
    check_time = db.Column(db.DateTime, default=datetime.utcnow)

    url = db.relationship(Url, back_populates='checks')
    check = db.relationship(Check, back_populates='urls')


"""
class Cluster(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    description = db.Column(db.String(150))

    dataframes = db.relationship(DataFrame, secondary='DataFrameCluster', backref='clusters', lazy='select')


DataFrameCluster = db.Table(
    'dataframe_cluster',
    db.Column('dataframe_id', db.Integer, db.ForeignKey(DataFrame.id)),
    db.Column('cluster_id', db.Integer, db.ForeignKey(Cluster.id))
)

"""