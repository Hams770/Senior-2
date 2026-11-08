"""Create the first admin account:  python -m app.cli create-admin admin@example.com 'StrongPass123'"""
import sys

from sqlalchemy import select

from .db import Base, SessionLocal, engine
from .models import User
from .security import hash_password


def create_admin(email: str, password: str) -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email.lower())):
            print("User already exists")
            return
        db.add(User(email=email.lower(), full_name="Administrator", role="admin",
                    password_hash=hash_password(password)))
        db.commit()
        print("Admin created:", email)


if __name__ == "__main__":
    if len(sys.argv) != 4 or sys.argv[1] != "create-admin":
        sys.exit(__doc__)
    create_admin(sys.argv[2], sys.argv[3])
