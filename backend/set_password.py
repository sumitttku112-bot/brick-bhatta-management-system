"""
Set (or reset) a user's password from the command line.

Usage (from the backend folder):
    python set_password.py +919876543210 'NewPassw0rd'
"""
import sys

from app.database import SessionLocal
from app import crud, security


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    phone, password = sys.argv[1], sys.argv[2]
    if len(password) < 6:
        print("Password must be at least 6 characters")
        sys.exit(1)

    db = SessionLocal()
    try:
        user = crud.get_user_by_phone(db, phone)
        if user is None or db.get(type(user), user.id) is None:
            print(f"No user in the users table with phone {phone}")
            sys.exit(1)
        user.password_hash = security.hash_password(password)
        db.commit()
        print(f"Password set for {user.name} ({user.id})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
