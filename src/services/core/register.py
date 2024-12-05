from src.models import User, db
from src.services.dao.user import UserDAO


def register_user(name: str, email: str, password: str) -> User:
    dao = UserDAO(db.session)
    user = dao.add(User(name=name, email=email, password=password))
    dao.commit()

    return user
