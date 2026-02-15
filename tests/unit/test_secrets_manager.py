import pytest
from config.secrets import SecretManager

@pytest.mark.unit
class TestSecretManager:
    def test_encrypt_decrypt_cycle(self):
        """平文を暗号化し、正しく復号できることを確認."""
        secret_key = "my_super_secret_key_for_testing"
        manager = SecretManager(secret_key)
        
        plaintext = "this is a secret message"
        encrypted = manager.encrypt(plaintext)
        decrypted = manager.decrypt(encrypted)
        
        assert encrypted != plaintext # 暗号化されていることを確認
        assert decrypted == plaintext # 正しく復号されることを確認

    def test_decrypt_invalid_ciphertext_returns_original(self):
        """無効な暗号文を復号しようとした場合、元の暗号文が返されることを確認."""
        secret_key = "my_super_secret_key_for_testing"
        manager = SecretManager(secret_key)
        
        invalid_ciphertext = "not_a_valid_encrypted_string"
        decrypted = manager.decrypt(invalid_ciphertext)
        
        # SecretManager.decrypt は失敗時にそのまま返す実装
        assert decrypted == invalid_ciphertext

    def test_is_encrypted(self):
        """値が暗号化されているかどうかの判定をテスト."""
        assert SecretManager.is_encrypted("encrypted:some_value") is True
        assert SecretManager.is_encrypted("plain_text") is False
        assert SecretManager.is_encrypted("") is False
        assert SecretManager.is_encrypted(None) is False # type: ignore

    def test_extract_encrypted_value(self):
        """暗号化された値から実際の暗号文を抽出できることをテスト."""
        assert SecretManager.extract_encrypted_value("encrypted:actual_cipher") == "actual_cipher"
        assert SecretManager.extract_encrypted_value("plain_text") == "plain_text" # 接頭辞がない場合はそのまま
        assert SecretManager.extract_encrypted_value("") == ""

    def test_default_secret_key(self):
        """secret_keyが指定されない場合にデフォルト値が使われることを確認."""
        manager = SecretManager()
        assert manager.secret_key == "default-secret-key-change-in-production"
        
        plaintext = "another secret"
        encrypted = manager.encrypt(plaintext)
        decrypted = manager.decrypt(encrypted)
        assert decrypted == plaintext
