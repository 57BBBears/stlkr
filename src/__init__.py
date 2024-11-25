from logging.config import dictConfig

# import rq
from flask import Flask
from flask_bootstrap import Bootstrap
from flask_migrate import Migrate

# from redis import Redis
from src.models import db
from src.services.auth import login_manager
from src.services.mail import mail
from src.views import admin, core


def create_app(config: str = "config.Config"):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config)

    if app.config["LOG_CONFIG"] is not None:
        dictConfig(app.config["LOG_CONFIG"])

    admin.admin.init_app(app)
    Bootstrap(app)
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    Migrate(app, db, render_as_batch=True)

    # app.redis = Redis.from_url(app.config["REDIS_URL"])
    # app.queue = {
    #     queue: rq.Queue(
    #         queue,
    #         connection=app.redis,
    #         default_timeout=app.config["TASK_EXECUTION_TIME"],
    #     )
    #     for queue in app.config["QUEUES"]
    # }

    # routes
    app.register_blueprint(core.bp)

    return app
