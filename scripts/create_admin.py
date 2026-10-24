"""
Creates (or promotes) an admin user. Admin login uses email + password.

Usage:
    python -m scripts.create_admin --email admin@example.com --password 'S3cret!pass' \
        --name "مدیر" --cellphone 09120000000

If a user with that email already exists, it is promoted to admin and its
password is reset. Without --password you are prompted for one (hidden input).
"""
import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import User


def main() -> int:
    ap = argparse.ArgumentParser(description="Create or promote an admin user")
    ap.add_argument("--email", required=True)
    ap.add_argument("--password")
    ap.add_argument("--name", default="Admin")
    ap.add_argument("--cellphone", default=None)
    args = ap.parse_args()

    password = args.password or getpass.getpass("Password: ")
    if len(password) < 8:
        print("Password must be at least 8 characters.")
        return 1

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == args.email).first()
        created = user is None
        if created:
            user = User(email=args.email)
            db.add(user)
        user.name = args.name or user.name
        if args.cellphone:
            user.cellphone = args.cellphone
        user.password = hash_password(password)
        user.is_admin = 1
        user.deleted_at = None
        db.commit()
        print(f"{'Created' if created else 'Updated'} admin: {args.email} (id={user.id})")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
