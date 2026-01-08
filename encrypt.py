import base64
from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv
import sys

password_to_encrypt = sys.argv[1].encode('utf-8')

load_dotenv()
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')


def encrypt_two_way(password: bytes, key: bytes) -> bytes:
    """Encrypt a password using Fernet (two-way)."""
    cipher = Fernet(key)
    return cipher.encrypt(password)



print(encrypt_two_way(password_to_encrypt, ENCRYPTION_KEY.encode('utf-8')).decode('utf-8'))
