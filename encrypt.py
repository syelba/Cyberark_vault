import bcrypt
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from cryptography.fernet import Fernet
import time
import os
import sys
from dotenv import load_dotenv
import importlib.util
from aam_python import *
load_dotenv()
ENCRYPTION_KEY = '' 

def salt_one_way(password: bytes) -> bytes:
    """Hash a password using bcrypt (one-way)."""
    return bcrypt.hashpw(password, bcrypt.gensalt())

def encrypt_two_way(password: bytes, key: bytes) -> bytes:
    """Encrypt a password using Fernet (two-way)."""
    cipher = Fernet(key)
    return cipher.encrypt(password)


def decrypt_password(encrypted_password: bytes, key: bytes) -> bytes:
    """Decrypt a password using Fernet."""
    cipher = Fernet(key)
    return cipher.decrypt(encrypted_password)

start_time = time.time()
# Test the functions

if __name__ == '__main__':
    # Load environment variables from .env file
    

    # Establish new session  
    base_uri = os.getenv('AAM_BASE_URI', 'https://passwordvault.intel.com')
    aimccp = CCPPasswordREST(base_uri=base_uri)

    # Load certificate based on available environment variables
    # Priority: Method 2 (file paths) > Method 3 (certificate content)
    if os.getenv('AAM_DEMO_PATH') and os.getenv('AAM_PASSPHRASE'):
        # Method 2: Load from file paths in environment variables
        cert_path = os.getenv('AAM_DEMO_PATH')
        passphrase_var = 'AAM_PASSPHRASE'
        key_path_var = 'AAM_DEMO_KEY_PATH' if os.getenv('AAM_DEMO_KEY_PATH') else None
        aimccp.load_cert_from_env_path('AAM_DEMO_PATH', passphrase_var, key_path_var)
        print('Loaded certificate from file path')
    elif os.getenv('AAM_CERT') and os.getenv('AAM_PASSPHRASE'):
        # Method 3: Load from certificate content in environment variables
        cert_var = 'AAM_CERT'
        passphrase_var = 'AAM_PASSPHRASE'
        key_var = 'AAM_KEY' if os.getenv('AAM_KEY') else None
        aimccp.load_cert_from_env(cert_var, passphrase_var, key_var)
        print('Loaded certificate from environment variable content')
    else:
        raise Exception('ERROR: Certificate configuration not found in .env file. Please configure AAM_DEMO_PATH or AAM_CERT variables.')

    # Get password using parameters from .env file
    appid = os.getenv('AAM_APP_ID')
    safe = os.getenv('AAM_SAFE')
    object_name = os.getenv('AAM_OBJECT_NAME')
    username = os.getenv('AAM_USERNAME')
    folder = os.getenv('AAM_FOLDER')
    address = os.getenv('AAM_ADDRESS')
    database = os.getenv('AAM_DATABASE')
    policy_id = os.getenv('AAM_POLICY_ID')
    reason = os.getenv('AAM_REASON')
    query_format = os.getenv('AAM_QUERY_FORMAT')
    dual_accounts = os.getenv('AAM_DUAL_ACCOUNTS', 'false').lower() == 'true'

    response = aimccp.get_password(
        appid=appid,
        safe=safe,
        objectName=object_name,
        username=username,
        folder=folder,
        address=address,
        database=database,
        policyid=policy_id,
        reason=reason,
        query_format=query_format,
        dual_accounts=dual_accounts
    )

    print('Full Python Object: {}'.format(response))  
    print('Username: {}'.format(response['UserName']))  
    print('Password: {}'.format(response['Content']))


print("Decrypted password:", decrypt_password(response['Content'].encode(), ENCRYPTION_KEY.encode()).decode())
stop_time = time.time()
print(f"Execution time: {stop_time - start_time} seconds")
