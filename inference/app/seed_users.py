from passlib.context import CryptContext

from inference.app.database import create_user, init_db


password_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


def hash_password(password: str) -> str:
    return password_context.hash(password)


def main():
    init_db()

    doctor = create_user(
        username="doctor01",
        password_hash=hash_password("doctor123"),
        full_name="Doctor User",
        role="doctor",
    )

    admin = create_user(
        username="admin01",
        password_hash=hash_password("admin123"),
        full_name="System Admin",
        role="admin",
    )

    print("Seeded users:")
    print(doctor)
    print(admin)


if __name__ == "__main__":
    main()