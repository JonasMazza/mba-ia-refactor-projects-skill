from datetime import datetime, timezone

import bcrypt

from database import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    # bcrypt hash; 60 chars typical but field allows up to 255 for safety.
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default="user")
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """Public serialization — allowlist; NEVER include password."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "active": self.active,
            "created_at": str(self.created_at),
        }

    def set_password(self, pwd: str) -> None:
        if not isinstance(pwd, str) or not pwd:
            raise ValueError("password must be a non-empty string")
        hashed = bcrypt.hashpw(pwd.encode("utf-8"), bcrypt.gensalt())
        self.password = hashed.decode("utf-8")

    def check_password(self, pwd: str) -> bool:
        if not self.password or not isinstance(pwd, str):
            return False
        try:
            return bcrypt.checkpw(pwd.encode("utf-8"), self.password.encode("utf-8"))
        except ValueError:
            # Stored value isn't a bcrypt hash (e.g. legacy MD5) — fail closed.
            return False

    def is_admin(self) -> bool:
        return self.role == "admin"
