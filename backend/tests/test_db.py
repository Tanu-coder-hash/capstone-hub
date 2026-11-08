import pytest

from app.core import db


def test_get_db_yields_session_and_closes_it(monkeypatch):
    class FakeSession:
        closed = False

        def close(self):
            self.closed = True

    fake_session = FakeSession()

    monkeypatch.setattr(
        db,
        "SessionLocal",
        lambda: fake_session,
    )

    generator = db.get_db()

    session = next(generator)

    assert session is fake_session
    assert fake_session.closed is False

    with pytest.raises(StopIteration):
        next(generator)

    assert fake_session.closed is True