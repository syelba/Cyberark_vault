import bcrypt
import sys

password_to_salt = sys.argv[1].encode('utf-8')


def salt_one_way(password: bytes) -> bytes:
    """Hash a password using bcrypt (one-way)."""
    return bcrypt.hashpw(password, bcrypt.gensalt())


print(salt_one_way(password_to_salt).decode('utf-8'))


