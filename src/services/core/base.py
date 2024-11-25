from src.models import User, db
from src.services.dao.user import UserDAO


def get_user(login: str) -> User | None:
    dao = UserDAO(db.session)

    return dao.get_by_email(login)
