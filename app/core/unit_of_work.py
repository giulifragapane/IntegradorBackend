# app/core/unit_of_work.py
from datetime import datetime, timezone

from fastapi import Depends
from sqlmodel import Session

from app.core.database import get_session


class UnitOfWork:

    def __init__(self, session: Session) -> None:
        self._session = session
        self.now = datetime.now(timezone.utc)

    @property
    def session(self) -> Session:
        return self._session

    def __enter__(self) -> "UnitOfWork":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is None:
            self._session.commit()
        else:
            self._session.rollback()

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()


def get_uow(session: Session = Depends(get_session)) -> UnitOfWork:
    return UnitOfWork(session)