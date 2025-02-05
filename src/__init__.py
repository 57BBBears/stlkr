from logging.config import dictConfig

# import rq
from flask import Flask
from flask_bootstrap import Bootstrap4
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

from config import Config
from src.models import db
from src.services.auth import login_manager
from src.services.mail import mail
from src.views import core, public
from src.views.admin import admin


def create_app(config: type[Config] = Config):
    app = Flask(
        __name__,
        host_matching=True,
        static_folder="static",
        static_host=config.CORE_DOMAIN,
        instance_relative_config=True,
    )
    app.config.from_object(config)
    app.static_host = app.config["CORE_DOMAIN"]

    if app.config["LOG_CONFIG"] is not None:
        dictConfig(app.config["LOG_CONFIG"])

    Bootstrap4(app)
    CSRFProtect(app)
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
    admin.init_app(app)
    app.register_blueprint(core.bp)
    public.bp.template_folder = config.PUBLIC_TEMPLATE_FOLDER
    app.register_blueprint(public.bp)

    return app
