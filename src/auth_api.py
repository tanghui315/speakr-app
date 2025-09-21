from __future__ import annotations

from datetime import timedelta
from typing import Optional

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)
from sqlalchemy.orm import Session

from .extensions import bcrypt, db

auth_bp = Blueprint("auth_api", __name__, url_prefix="/api/auth")


def _get_session() -> Session:
    return db.session


def _get_user_model():
    user_model = current_app.config.get("AUTH_USER_MODEL")
    if user_model is None:
        raise RuntimeError("AUTH_USER_MODEL not configured on Flask app")
    return user_model


@auth_bp.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    email = payload.get("email")
    password = payload.get("password")

    if not email or not password:
        return jsonify({"error": "Missing email or password"}), 400

    session = _get_session()
    user_model = _get_user_model()
    user: Optional[object] = session.query(user_model).filter_by(email=email).first()

    demo_mode = current_app.config.get("AUTH_DEMO_MODE", False)
    demo_email = current_app.config.get("AUTH_DEMO_EMAIL")
    demo_password = current_app.config.get("AUTH_DEMO_PASSWORD")

    password_valid = False
    if user and password:
        try:
            password_valid = bcrypt.check_password_hash(user.password, password)
        except ValueError:
            password_valid = False

    # Allow demo credentials fallback when enabled
    if demo_mode and email == demo_email and password == demo_password:
        if not user:
            # optionally auto-create demo user if not present
            user = user_model(email=email, username=email.split('@')[0], password=bcrypt.generate_password_hash(password).decode('utf-8'))
            session.add(user)
            session.commit()
        password_valid = True

    if not user or not password_valid:
        return jsonify({"error": "Invalid credentials"}), 401

    identity = {"id": user.id, "email": user.email}
    access_expires = current_app.config.get("JWT_ACCESS_TOKEN_EXPIRES", timedelta(minutes=15))
    refresh_expires = current_app.config.get("JWT_REFRESH_TOKEN_EXPIRES", timedelta(days=30))

    access_token = create_access_token(identity=identity, expires_delta=access_expires)
    refresh_token = create_refresh_token(identity=identity, expires_delta=refresh_expires)

    return jsonify(
        {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": user.id,
                "email": user.email,
                "name": getattr(user, "name", None),
            },
        }
    )


@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    access_expires = current_app.config.get("JWT_ACCESS_TOKEN_EXPIRES", timedelta(minutes=15))
    access_token = create_access_token(identity=identity, expires_delta=access_expires)
    return jsonify({"access_token": access_token})


@auth_bp.post("/logout")
@jwt_required()
def logout():
    # TODO: implement token revocation/blacklist if required
    _ = get_jwt().get("jti")
    return jsonify({"success": True})
