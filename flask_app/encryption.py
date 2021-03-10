import cryptography
from cryptography.fernet import Fernet


def generate_key():
    key = Fernet.generate_key()
    return key


def encrypt(message, key):
    f = Fernet(key)
    encrypted = f.encrypt(message)
    return encrypted


def decrypt(encrypted, key):
    f = Fernet(key)
    decrypted = f.decrypt(encrypted)
    return decrypted

