"""
tests/test_watchlist.py — CineLog

Tests for the watchlist service.
Following the same patterns as test_collection.py.
"""

import pytest
from app import create_app, db
from models import User, Film, WatchlistEntry
from services.watchlist_service import (
    add_to_watchlist,
    remove_from_watchlist,
    get_watchlist,
    FilmNotFoundError,
    AlreadyInWatchlistError,
    NotInWatchlistError,
)


@pytest.fixture
def app():
    """Create an isolated test app with an in-memory database."""
    app = create_app(config={
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def sample_user(app):
    """A user to use in tests."""
    with app.app_context():
        user = User(username="testuser", email="test@example.com")
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def sample_film(app):
    """A film to use in tests."""
    with app.app_context():
        film = Film(title="Paddington 2", year=2017, genre="Comedy")
        db.session.add(film)
        db.session.commit()
        return film.id


# ── Nonexistent film ─────────────────────────────────────────────────────

def test_add_to_watchlist_nonexistent_film_raises(app, sample_user):
    """
    Adding a film_id that doesn't exist in the database should raise
    FilmNotFoundError, not a database integrity error.
    """
    with app.app_context():
        fake_film_id = "00000000-0000-0000-0000-000000000000"

        with pytest.raises(FilmNotFoundError):
            add_to_watchlist(user_id=sample_user, film_id=fake_film_id)


# ── Remove from watchlist ────────────────────────────────────────────────

def test_remove_from_watchlist_success(app, sample_user, sample_film):
    """
    Removing a film that exists in the watchlist should succeed
    and return True.
    """
    with app.app_context():
        # First add the film to the watchlist
        add_to_watchlist(user_id=sample_user, film_id=sample_film)

        # Verify it was added
        entry = WatchlistEntry.query.filter_by(
            user_id=sample_user, film_id=sample_film
        ).first()
        assert entry is not None

        # Now remove it
        result = remove_from_watchlist(user_id=sample_user, film_id=sample_film)
        assert result is True

        # Verify it was removed
        entry = WatchlistEntry.query.filter_by(
            user_id=sample_user, film_id=sample_film
        ).first()
        assert entry is None


def test_remove_from_watchlist_not_in_list_raises(app, sample_user, sample_film):
    """
    Attempting to remove a film that's not in the watchlist should raise
    NotInWatchlistError, not silently succeed or cause a database error.
    """
    with app.app_context():
        with pytest.raises(NotInWatchlistError):
            remove_from_watchlist(user_id=sample_user, film_id=sample_film)


# ── Deduplication ────────────────────────────────────────────────────────

def test_add_to_watchlist_duplicate_raises(app, sample_user, sample_film):
    """
    Adding the same film twice to the watchlist should raise
    AlreadyInWatchlistError, not silently create a duplicate entry.

    This ensures the deduplication logic works correctly and prevents
    database bloat from duplicate entries.
    """
    with app.app_context():
        # Add the film once
        add_to_watchlist(user_id=sample_user, film_id=sample_film)

        # Try to add it again - should raise
        with pytest.raises(AlreadyInWatchlistError):
            add_to_watchlist(user_id=sample_user, film_id=sample_film)

        # Verify only one entry exists
        count = WatchlistEntry.query.filter_by(
            user_id=sample_user, film_id=sample_film
        ).count()
        assert count == 1


# ── Visibility control ───────────────────────────────────────────────────

def test_add_to_watchlist_with_public_false(app, sample_user, sample_film):
    """
    Adding a film with public=False should create a private watchlist entry.
    This allows users to explicitly control visibility when adding films.
    """
    with app.app_context():
        entry = add_to_watchlist(
            user_id=sample_user, film_id=sample_film, public=False
        )

        assert entry is not None
        assert entry.public is False

        # Verify it persisted with the correct visibility
        in_db = WatchlistEntry.query.filter_by(
            user_id=sample_user, film_id=sample_film
        ).first()
        assert in_db is not None
        assert in_db.public is False


def test_add_to_watchlist_defaults_to_public(app, sample_user, sample_film):
    """
    Adding a film without specifying public parameter should default to
    public=True, matching the model default.
    """
    with app.app_context():
        entry = add_to_watchlist(user_id=sample_user, film_id=sample_film)

        assert entry is not None
        assert entry.public is True
