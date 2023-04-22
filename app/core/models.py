from slugify import slugify
import validators
from rq.job import Job
from rq.exceptions import NoSuchJobError
from redis.exceptions import ConnectionError, ResponseError
from rq.command import send_stop_job_command
from sqlalchemy import UniqueConstraint, distinct
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import validates
from sqlalchemy.sql import expression
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.types import DateTime
from sqlalchemy_utils import URLType
from flask import current_app
from app import db


# utcnow for postgresql
class utcnow(expression.FunctionElement):
    type = DateTime()
    inherit_cache = True

@compiles(utcnow, 'postgresql')
def pg_utcnow(element, compiler, **kw):
    return "TIMEZONE('utc', CURRENT_TIMESTAMP)"

class DataFrame(db.Model):
    """ Dataframe unites urls """
    __tablename__ = 'dataframe'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, info={'label': 'Название'})
    description = db.Column(db.String(150), info={'label': 'Описание'})
    # fk must be table name not model, use_alter to prevent unresolved cycles between check and dataframe
    check_id = db.Column(db.Integer, db.ForeignKey('dataframe_check.id', ondelete='set null', use_alter=True))

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
    properties = db.relationship('DataFrameProperty', back_populates='dataframe', lazy='select')

    @property
    def url_count(self):
        return db.session.query(Url.id).filter_by(dataframe=self).count()

    def __init__(self, name, description = None):
        self.name = name
        if description:
            self.description = description

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

    UniqueConstraint(dataframe_id, url, name='unique_dataframe_id_url')

class Check(db.Model):
    """ Check is used for url parsing - connects urls data with the dataframe """
    __tablename__ = 'dataframe_check'
    id = db.Column(db.Integer, primary_key=True)
    dataframe_id = db.Column(db.Integer, db.ForeignKey(DataFrame.id, ondelete='cascade'), nullable=False)
    name = db.Column(db.String(50), nullable=False, info={'label': 'Название'})
    selectors = db.Column(db.Text, info={'label': 'Селекторы для извлечения данных'})  # TODO delete when use Property
    # for different dbs
    start_time = db.Column(db.DateTime, server_default=utcnow())
    #start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime)

    urls = db.relationship('UrlCheck', back_populates='check', lazy='select', cascade='all, delete-orphan')
    dataframe = db.relationship(DataFrame, back_populates='checks', foreign_keys=[dataframe_id], lazy='select')
    active_dataframe = db.relationship(DataFrame,
                                       back_populates='active_check',
                                       foreign_keys='[DataFrame.check_id]',
                                       uselist=False,
                                       lazy='select')

    @property
    def checked_url_count(self):
        return db.session.query(UrlCheck.id).filter_by(check=self).count()

    @property
    def handled_url_count(self):
        return db.session.query(distinct(UrlProperty.url_id)).filter_by(check_id=self.id).count()

    def start(self, queue='default', **kwargs) -> Job:
        job_id = self._get_check_data_job_id()
        app_queue = current_app.queue.get(queue, 'default')
        job = app_queue.enqueue('app.core.tasks.check_dataframe', self.id, job_id=job_id, **kwargs)

        return job

    def stop(self):
        job_id = self._get_check_data_job_id()
        self._stop_job(job_id)

    def _is_busy(self, task: str) -> bool:
        # check if the check has a job running
        task_name = '_get_' + task + '_data_job_id'
        con = self._get_queue_connection()
        get_job_id = getattr(self, task_name)
        job_id = get_job_id()

        try:
            job = Job.fetch(job_id, connection=con)
        except (ConnectionError, ResponseError, NoSuchJobError):
            return False

        job_status = job.get_status()

        return job_status in ['queued', 'started']

    def is_checking(self):
        return self._is_busy('check')

    def extract_data(self, queue='default', **kwargs) -> Job:
        #if self.is_extracting_data():
            #return False

        job_id = self._get_extract_data_job_id()
        app_queue = current_app.queue.get(queue, 'default')
        job = app_queue.enqueue('app.core.tasks.extract_data_from_check', self.id, job_id=job_id, **kwargs)

        return job

    def stop_extract_data(self):
        job_id = self._get_extract_data_job_id()
        self._stop_job(job_id)

    def is_extracting_data(self) -> bool:
        return self._is_busy('extract')

    @staticmethod
    def _get_queue_connection():
        return current_app.redis

    def _get_extract_data_job_id(self) -> str:
        return f'check_extract_data_{self.id}'

    def _get_check_data_job_id(self) -> str:
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

        job.delete()

class UrlCheck(db.Model):
    """ A table for many to many Url-Check relationship """
    id = db.Column(db.Integer, primary_key=True)
    url_id = db.Column(db.Integer, db.ForeignKey(Url.id, ondelete='cascade'), nullable=False)
    check_id = db.Column(db.Integer, db.ForeignKey(Check.id, ondelete='cascade'), nullable=False)
    status = db.Column(db.Integer)
    raw_data = db.Column(db.Text) # TODO default='' ?
    # for different dbs ?
    check_time = db.Column(db.DateTime, server_default=utcnow())
    #last_modified = db.Column(db.DateTime, onupdate=utcnow())
    #check_time = db.Column(db.DateTime, default=datetime.utcnow)
    #last_modified = db.Column(db.DateTime, onupdate=datetime.utcnow)

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
    db.Column('dataframe_id', db.Integer, db.ForeignKey(DataFrame.id, ondelete='cascade'), primary_key=True),
    db.Column('cluster_id', db.Integer, db.ForeignKey(Cluster.id, ondelete='cascade'), primary_key=True)
)

class Property(db.Model):
    """ Dataframe settings for extracting data - selectors we get """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, info={'label': 'Название'})
    code = db.Column(db.String(50), unique=True, nullable=False)

    dataframes = db.relationship('DataFrameProperty', back_populates='property', lazy='select')

    def __str__(self):
        return self.name

    #dataframes = db.relationship(DataFrame, secondary='DataFrameProperty', back_populates='properties', lazy='select')

class DataFrameProperty(db.Model):
    __tablename__ = 'dataframe_property'
    id = db.Column(db.Integer, primary_key=True)
    dataframe_id = db.Column(db.Integer, db.ForeignKey(DataFrame.id, ondelete='cascade'), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey(Property.id, ondelete='cascade'), nullable=False)
    selector = db.Column(db.String(50), nullable=False, info={'label': 'xpath'})

    UniqueConstraint(dataframe_id, property_id, name='unique_dataframe_id_property_id')

    dataframe = db.relationship(DataFrame, back_populates='properties', lazy='select')
    property = db.relationship(Property, back_populates='dataframes', lazy='select')

class UrlProperty(db.Model):
    """ A table for an Url-Check-Property relation """
    id = db.Column(db.Integer, primary_key=True)
    url_id = db.Column(db.Integer, db.ForeignKey(Url.id, ondelete='cascade'), nullable=False)
    check_id = db.Column(db.Integer, db.ForeignKey(Check.id, ondelete='cascade'), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey(Property.id, ondelete='cascade'), nullable=False)
    data = db.Column(db.Text, nullable=False)

    UniqueConstraint(url_id, check_id, property_id, name='unique_url_check_property')
