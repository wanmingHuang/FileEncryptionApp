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


def encrypt_file(file_name, key):
    with open(file_name, 'rb') as f:
        content = f.read()  # Read the bytes of the input file
    encrypted = encrypt(content, key)
    with open(file_name, 'wb') as f:
        f.write(encrypted)

def decrypt_file(file_name, key):
    with open(file_name, 'rb') as f:
        content = f.read()  # Read the bytes of the input file
    decrypted = decrypt(content, key)
    with open(file_name, 'wb') as f:
        f.write(decrypted)
