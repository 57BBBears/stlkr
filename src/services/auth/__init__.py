from flask_login import LoginManager

from src.models import db
from src.services.dao.user import UserDAO

login_manager = LoginManager()
login_manager.login_view = "core.index"


@login_manager.user_loader
def load_user(user_id: str):
    dao = UserDAO(db.session)

    return dao.get(int(user_id))
