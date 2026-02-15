import pytest
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from config.secrets import SecretManager

@pytest.fixture
def secret_key():
    return "test_secret_key_32bytes_for_unit_test"

@pytest.fixture
def secret_manager(secret_key):
    return SecretManager(secret_key)

def test_secret_manager_encryption_decryption(secret_manager):
    original_value = "my_secret_password"
    encrypted_value = secret_manager.encrypt(original_value)
    assert encrypted_value.startswith("encrypted:")

    decrypted_value = secret_manager.decrypt(encrypted_value)
    assert decrypted_value == original_value

def test_secret_manager_is_encrypted():
    assert SecretManager.is_encrypted("encrypted:some_value") is True
    assert SecretManager.is_encrypted("plain_value") is False
    assert SecretManager.is_encrypted("") is False
    assert SecretManager.is_encrypted(None) is False

def test_secret_manager_extract_encrypted_value():
    assert SecretManager.extract_encrypted_value("encrypted:some_value") == "some_value"
    with pytest.raises(ValueError):
        SecretManager.extract_encrypted_value("plain_value")