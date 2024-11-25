from sqlalchemy import select

from src.models import User
from src.services.dao.base import BaseDAO


class UserDAO(BaseDAO[User]):
    def __init__(self, session, *args, **kwargs):
        super().__init__(User, session, *args, **kwargs)

    def get_by_email(self, email: str) -> User | None:
        result = self.session.scalars(
            select(self.model).where(self.model.email == email)
        )

        return result.one_or_none()
