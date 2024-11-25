from typing import Generic, Sequence, TypeVar

from sqlalchemy import exc, insert, select, update
from sqlalchemy.orm import Session

from src.models import Base
from src.services.dao.exceptions import IntegrityError

Model = TypeVar("Model", bound=Base)


class BaseDAO(Generic[Model]):
    def __init__(self, model: type(Model), session: Session, *args, **kwargs):
        """
        ORM queries for an abstract table.
        :param model:
        :param session:
        """
        self.model = model
        self.session = session

    def add(self, model: Model) -> int:
        try:
            self.session.add(model)
            self.session.flush([model])

            return model.id

        except exc.IntegrityError as e:
            raise IntegrityError() from e

    def update(self, updates: list[dict]):
        try:
            self.session.execute(update(self.model), updates)
        except exc.IntegrityError as e:
            raise IntegrityError() from e

    def insert(self, inserts: list[dict]):
        try:
            stmt = insert(self.model)
            self.session.execute(stmt, inserts)
        except exc.IntegrityError as e:
            raise IntegrityError() from e

    def expunge(self, model: Model):
        self.session.expunge(model)

    def get_all(self) -> Sequence[Model]:
        """
        :return: List of models.
        """
        query = select(self.model)
        result = self.session.scalars(query)

        return result.all()

    def get(self, model_id: int) -> Model | None:
        """
        :param model_id: input id
        :return:
        """
        result = self.session.execute(
            select(self.model).where(self.model.id == model_id)
        )

        return result.one_or_none()

    def flush(self):
        self.session.flush()

    def commit(self):
        self.session.commit()

    def refresh(self, model: Model):
        self.session.refresh(model)

    def merge(self, model: Model) -> Model:
        return self.session.merge(model)

    def rollback(self):
        self.session.rollback()

    def delete(self, model: Model):
        self.session.delete(model)
