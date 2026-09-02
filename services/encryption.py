import os
from cryptography.fernet import Fernet

# Read encryption key from environment variable
# If not present, look for a local .key file or generate one securely
encryption_key_env = os.getenv("QUALIX_ENCRYPTION_KEY")

if encryption_key_env:
    ENCRYPTION_KEY = encryption_key_env.encode("utf-8")
else:
    KEY_FILE = ".key"
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as kf:
            ENCRYPTION_KEY = kf.read()
    else:
        ENCRYPTION_KEY = Fernet.generate_key()
        # Save locally for development persistence
        with open(KEY_FILE, "wb") as kf:
            kf.write(ENCRYPTION_KEY)

cipher_suite = Fernet(ENCRYPTION_KEY)

def encrypt_data(content: bytes) -> bytes:
    """Encrypts raw byte string using Fernet AES-256."""
    return cipher_suite.encrypt(content)

def decrypt_data(token: bytes) -> bytes:
    """Decrypts Fernet token back to raw bytes."""
    return cipher_suite.decrypt(token)
