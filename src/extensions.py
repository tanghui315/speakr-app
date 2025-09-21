from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_jwt_extended import JWTManager

# Shared Flask extensions

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
limiter = Limiter(
    get_remote_address,
    app=None,
    default_limits=["5000 per day", "1000 per hour"],
)
jwt = JWTManager()

__all__ = ["db", "bcrypt", "login_manager", "limiter", "jwt"]
