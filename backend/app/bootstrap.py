import logging
import os

from . import crud, models, security
from .database import SessionLocal

logger = logging.getLogger(__name__)


def bootstrap_admin():
    """
    If ADMIN_PHONE and ADMIN_PASSWORD are set, create (or reset the password of)
    an Admin user with that phone number. Intended for first-time setup: set the
    env vars once, deploy, log in, then remove them.
    """
    phone = os.getenv("ADMIN_PHONE", "").replace(" ", "")
    password = os.getenv("ADMIN_PASSWORD")
    if not phone or not password:
        return
    if len(password) < 6:
        logger.error("ADMIN_PASSWORD must be at least 6 characters - skipping admin bootstrap")
        return

    phone = "+" + phone.lstrip("+")
    db = SessionLocal()
    try:
        user = crud.get_user_for_login(db, phone)
        if user:
            user.password_hash = security.hash_password(password)
            user.is_active = True
            logger.warning("Bootstrap: password reset for existing user %s", user.id)
        else:
            user = models.User(
                id="admin_" + phone[-10:],
                name="Admin",
                name_hindi="व्यवस्थापक",
                role="Admin",
                role_hindi="व्यवस्थापक",
                initials="AD",
                is_active=True,
                phone_number=phone,
                password_hash=security.hash_password(password),
            )
            db.add(user)
            logger.warning("Bootstrap: created Admin user %s", user.id)
        db.commit()
    finally:
        db.close()
