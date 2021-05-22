import cryptography
from cryptography.fernet import Fernet
import uuid


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


def encrypt_file(content, sample_name_extension, key):
    # with open(file_name, 'rb') as f:
    #     content = f.read()  # Read the bytes of the input file
    encrypted = encrypt(content, key)
    tmpfilename = str(uuid.uuid4()) + "." + sample_name_extension
    with open(tmpfilename, 'wb') as f:
        f.write(encrypted)
    return tmpfilename

def decrypt_file(content, sample_name_extension, key):
    # with open(file_name, 'rb') as f:
    #     content = f.read()  # Read the bytes of the input file
    decrypted = decrypt(content, key)
    tmpfilename = str(uuid.uuid4()) + "." + sample_name_extension
    with open(tmpfilename, 'wb') as f:
        f.write(decrypted)
    return tmpfilename
