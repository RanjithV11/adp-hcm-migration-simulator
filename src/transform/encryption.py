# Simple encryption for SSN (demo - use proper key management in prod)
from cryptography.fernet import Fernet
import os

_KEY_FILE = '.encryption_key'

def get_or_create_key():
    if os.path.exists(_KEY_FILE):
        with open(_KEY_FILE, 'rb') as f:
            return f.read()
    key = Fernet.generate_key()
    with open(_KEY_FILE, 'wb') as f:
        f.write(key)
    return key

_cipher = Fernet(get_or_create_key())

def encrypt_ssn(ssn):
    '''Encrypt SSN after cleaning'''
    if not ssn:
        return None
    # Clean: remove dashes, spaces
    clean = ''.join(c for c in ssn if c.isdigit())
    if len(clean) != 9:
        raise ValueError(f'Invalid SSN format: {ssn}')
    # Format as XXX-XX-XXXX for storage, then encrypt
    formatted = f'{clean[:3]}-{clean[3:5]}-{clean[5:]}'
    return _cipher.encrypt(formatted.encode()).decode()

def decrypt_ssn(encrypted):
    if not encrypted:
        return None
    return _cipher.decrypt(encrypted.encode()).decode()
