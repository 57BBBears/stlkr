from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
from config import Config
from redis import Redis
import rq
from logging.config import dictConfig


db = SQLAlchemy()
migrate = Migrate()


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    if app.config['LOG_CONFIG']:
        dictConfig(app.config['LOG_CONFIG'])

    db.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)
    Bootstrap(app)
    app.redis = Redis.from_url(app.config['REDIS_URL'])
    app.queue = {queue: rq.Queue(queue, connection=app.redis) for queue in app.config['QUEUES']}
    # routes
    from app import routes
    app.register_blueprint(routes.bp)

    return app
