from logging.config import dictConfig
from flask import Flask, abort
from flask_migrate import Migrate
from flask_bootstrap import Bootstrap
from flask_login import LoginManager, current_user
from redis import Redis
import rq

from app.models import db, User
from config import Config

login = LoginManager()
@login.user_loader
def load_user(user_id: int):
    return User.query.get(int(user_id))
login.login_view = 'auth.login'
migrate = Migrate()


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    if app.config['LOG_CONFIG'] is not None:
        dictConfig(app.config['LOG_CONFIG'])

    db.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)

    Bootstrap(app)

    app.redis = Redis.from_url(app.config['REDIS_URL'])
    app.queue = {queue: rq.Queue(queue, connection=app.redis, default_timeout=app.config['TASK_EXECUTION_TIME'])
                 for queue in app.config['QUEUES']}

    login.init_app(app)
    # routes
    from app.core import bp as core_bp
    from app.pages import bp as pages_bp
    from app.auth import bp as auth_bp

    @core_bp.before_request
    def only_admin_allowed():
        if not current_user.is_authenticated:
            abort(403)

    app.register_blueprint(pages_bp)
    app.register_blueprint(core_bp, url_prefix='/admin')
    app.register_blueprint(auth_bp, url_prefix='/auth')

    return app
