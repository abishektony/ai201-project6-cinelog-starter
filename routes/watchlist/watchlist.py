"""
routes/watchlist/watchlist.py — CineLog

Endpoints for a user's watchlist.
"""

from flask import Blueprint, jsonify, request
from services.watchlist_service import (
    add_to_watchlist,
    remove_from_watchlist,
    get_watchlist,
    FilmNotFoundError,
    AlreadyInWatchlistError,
    NotInWatchlistError,
)

watchlist_bp = Blueprint("watchlist", __name__)


@watchlist_bp.route("/<user_id>", methods=["GET"])
def view_watchlist(user_id):
    """
    GET /watchlist/<user_id>

    Returns all films in a user's watchlist, sorted newest-first.
    """
    films = get_watchlist(user_id)
    return jsonify(films)


@watchlist_bp.route("/<user_id>/add", methods=["POST"])
def add_film(user_id):
    """
    POST /watchlist/<user_id>/add

    Body: { "film_id": "<uuid>", "public": <bool> }
    The public field is optional and defaults to True.
    """
    data = request.get_json()
    if not data or "film_id" not in data:
        return jsonify({"error": "film_id is required"}), 400

    # Get the public parameter, defaulting to True if not provided
    public = data.get("public", True)

    try:
        entry = add_to_watchlist(
            user_id=user_id, film_id=data["film_id"], public=public
        )
        return jsonify(entry.to_dict()), 201
    except FilmNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except AlreadyInWatchlistError as e:
        return jsonify({"error": str(e)}), 409


@watchlist_bp.route("/<user_id>/remove", methods=["DELETE"])
def remove_film(user_id):
    """
    DELETE /watchlist/<user_id>/remove

    Body: { "film_id": "<uuid>" }
    """
    data = request.get_json()
    if not data or "film_id" not in data:
        return jsonify({"error": "film_id is required"}), 400

    try:
        remove_from_watchlist(user_id=user_id, film_id=data["film_id"])
        return jsonify({"message": "Removed from watchlist"}), 200
    except NotInWatchlistError as e:
        return jsonify({"error": str(e)}), 404