from datetime import datetime
from slugify import slugify
import validators
from rq.job import Job
from rq.command import send_stop_job_command
from sqlalchemy import UniqueConstraint
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.sql import func
from sqlalchemy.orm import validates
from sqlalchemy_utils import URLType
from flask import current_app
from app import db


class DataFrame(db.Model):
    """ Dataframe unites urls """
    __tablename__ = 'dataframe'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, info={'label': 'Название'})
    description = db.Column(db.String(150), info={'label': 'Описание'})
    # fk must be table name not model, use_alter to prevent unresolved cycles between check and dataframe
    check_id = db.Column(db.Integer, db.ForeignKey('check.id', ondelete='set null', use_alter=True))

    active_check = db.relationship('Check',
                                   back_populates='active_dataframe',
                                   foreign_keys=[check_id],
                                   lazy='select')
    urls = db.relationship('Url', back_populates='dataframe', lazy='select', cascade='all, delete-orphan')
    checks = db.relationship('Check',
                             back_populates='dataframe',
                             foreign_keys='[Check.dataframe_id]',
                             lazy='select',
                             cascade='all, delete-orphan',
                             order_by='desc(Check.id)')
    clusters = db.relationship('Cluster', secondary='dataframe_cluster', back_populates='dataframes', lazy='select')

    @property
    def url_count(self):
        return Url.query.filter_by(dataframe=self).count()

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name


class Url(db.Model):
    """ Urls to check """
    id = db.Column(db.Integer, primary_key=True)
    dataframe_id = db.Column(db.Integer, db.ForeignKey(DataFrame.id, ondelete='cascade'), nullable=False)
    url = db.Column(URLType())

    checks = db.relationship('UrlCheck', back_populates='url', lazy='select', cascade='all, delete-orphan')
    dataframe = db.relationship(DataFrame, back_populates='urls', lazy='select')

    @validates('url')
    def validate_url(self, key, url):
        if not validators.url(url):
            raise ValueError(f'{url} failed url validation.')

        return url
    # TODO add url dataframe_id unique constraint to avoid duplicates
    #UniqueConstraint(dataframe_id, url, name='unique_dataframe_id_url')


class Check(db.Model):
    """ Check is used for url parsing - connects urls data with the dataframe """
    #  __tablename__ = 'dataframe_check'  TODO uncomment before initial db upgrade
    id = db.Column(db.Integer, primary_key=True)
    dataframe_id = db.Column(db.Integer, db.ForeignKey(DataFrame.id, ondelete='cascade'), nullable=False)
    name = db.Column(db.String(50), nullable=False, info={'label': 'Название'})
    selectors = db.Column(db.Text, info={'label': 'Селекторы в json формате'})  # TODO delete when use Property
    #start_time = db.Column(db.DateTime, server_default=func.utc_timestamp())
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime)

    urls = db.relationship('UrlCheck', back_populates='check', lazy='select', cascade='all, delete-orphan')
    dataframe = db.relationship(DataFrame, back_populates='checks', foreign_keys=[dataframe_id], lazy='select')
    active_dataframe = db.relationship(DataFrame,
                                       back_populates='active_check',
                                       foreign_keys='[DataFrame.check_id]',
                                       uselist=False,
                                       lazy='select')

    def start(self, queue='default', **kwargs) -> Job:
        job_id = self._get_getting_data_job_id()
        app_queue = current_app.queue.get(queue, 'default')
        job = app_queue.enqueue('app.tasks.check_dataframe', self.id, job_id=job_id, **kwargs)

        return job

    def stop(self):
        job_id = self._get_getting_data_job_id()
        self._stop_job(job_id)

    def is_checking(self):
        ...

    def extract_data(self, queue='default', **kwargs) -> Job:
        if self.is_extracting_data():
            return False

        job_id = self._get_extracting_data_job_id()
        app_queue = current_app.queue.get(queue, 'default')
        job = app_queue.enqueue('app.tasks.extract_data_from_check', self.id, job_id=job_id, **kwargs)

        return job

    def stop_extract_data(self):
        job_id = self._get_extracting_data_job_id()
        self._stop_job(job_id)

    def is_extracting_data(self) -> bool:
        con = current_app.redis
        job_id = self._get_extracting_data_job_id()
        job = Job.fetch(job_id, connection=con)
        job_status = job.get_status()

        return job_status in ['queued', 'started']

    def _get_extracting_data_job_id(self) -> str:
        return f'check_extract_data_{self.id}'

    def _get_getting_data_job_id(self) -> str:
        return f'check_get_data_{self.id}'

    @staticmethod
    def _stop_job(job_id):
        con = current_app.redis
        job = Job.fetch(job_id, connection=con)
        job_status = job.get_status()

        if job_status == 'started':
            send_stop_job_command(con, job_id)
        elif job_status == 'queued':
            job.cancel()


class UrlCheck(db.Model):
    """ A table for many to many Url-Check relationship """
    id = db.Column(db.Integer, primary_key=True)
    url_id = db.Column(db.Integer, db.ForeignKey(Url.id, ondelete='cascade'), nullable=False)
    check_id = db.Column(db.Integer, db.ForeignKey(Check.id, ondelete='cascade'), nullable=False)
    status = db.Column(db.Integer)
    raw_data = db.Column(db.Text)
    extracted_data = db.Column(db.Text)  # TODO delete when use Property
    #check_time = db.Column(db.DateTime, server_default=func.utc_timestamp())
    #last_modified = db.Column(db.DateTime, onupdate=func.utc_timestamp())
    check_time = db.Column(db.DateTime, default=datetime.utcnow)
    last_modified = db.Column(db.DateTime, onupdate=datetime.utcnow)

    url = db.relationship(Url, back_populates='checks')
    check = db.relationship(Check, back_populates='urls')

    UniqueConstraint(url_id, check_id, name='unique_url_id_check_id')


class Cluster(db.Model):
    """ Cluster unites dataframes, an analogue of section """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    slug = db.Column(db.String(105), nullable=False, unique=True)
    title = db.Column(db.String(100))
    description = db.Column(db.String(200))
    excerpt = db.Column(db.String(255))
    text = db.Column(db.Text)
    image = db.Column(db.Text)
    parent_id = db.Column(db.Integer, db.ForeignKey(id, ondelete='cascade'))

    parent = db.relationship('Cluster', backref=db.backref('children', cascade='all, delete'), remote_side=[id], lazy='select')
    dataframes = db.relationship(DataFrame, secondary='dataframe_cluster', back_populates='clusters', lazy='select')
    frames = association_proxy('dataframes', 'name')
    
    # TODO add name min length constraint due to not to be set blank

    @staticmethod
    def slugify(target, value, oldvalue, initiator):
        if value and (not target.slug or value != oldvalue):
            target.slug = slugify(value)


db.event.listen(Cluster.name, 'set', Cluster.slugify, retval=False)


DataFrameCluster = db.Table(
    'dataframe_cluster',
    db.Column('dataframe_id', db.Integer, db.ForeignKey(DataFrame.id, ondelete='cascade')),
    db.Column('cluster_id', db.Integer, db.ForeignKey(Cluster.id, ondelete='cascade'))
)


# TODO use instead of UrlCheck.extracted_data and Check.selectors
"""
class Property(db.Model):
    # Url property - data we get by parsing 
    id = db.Column(db.Integer, primary_key=True)
    dataframe_id = db.Column(db.Integer, db.ForeignKey(DataFrame.id, ondelete='cascade'), nullable=False)
    name = db.Column(db.String(50), nullable=False, info={'label': 'Имя'})
    code = db.Column(db.String(50), nullable=False)

    UniqueConstraint(dataframe_id, code, name='unique_dataframe_id_code')


class CheckSelector(db.Model):
    # A table for many to many Check-Property relation to fill selector for extracting data 
    id = db.Column(db.Integer, primary_key=True)
    check_id = db.Column(db.Integer, db.ForeignKey(Check.id, ondelete='cascade'), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey(Property.id, ondelete='cascade'), nullable=False)
    value = db.Column(db.Text, nullable=False)

    UniqueConstraint(check_id, property_id, name='unique_check_id_property_id')


class UrlProperty(db.Model):
    # A table for many to many Url-Property relation 
    id = db.Column(db.Integer, primary_key=True)
    urlcheck_id = db.Column(db.Integer, db.ForeignKey(UrlCheck.id, ondelete='cascade'))
    property_id = db.Column(db.Integer, db.ForeignKey(Property.id, ondelete='cascade'))
    value = db.Column(db.Text, nullable=False)

    UniqueConstraint(urlcheck_id, property_id, name='unique_urlcheck_id_property_id')
"""