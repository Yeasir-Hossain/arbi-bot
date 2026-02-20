"""
Security Utilities for AI Trading System
Encryption, credential management, and security helpers
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.backends import default_backend
import base64


class SecretsManager:
    """
    Secure secrets management with encryption
    
    Features:
    - Encrypt/decrypt sensitive data
    - Secure file storage
    - Key management
    """

    def __init__(self, key_file: str = "./config/.secrets.key"):
        """
        Initialize secrets manager
        
        Args:
            key_file: Path to encryption key file
        """
        self.key_file = Path(key_file)
        self.secrets_file = Path("./config/.secrets.enc")
        
        # Ensure config directory exists
        self.key_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load or generate encryption key
        self.key = self._load_or_generate_key()
        self.cipher = Fernet(self.key)
        
        logger.info("Secrets Manager initialized")

    def _load_or_generate_key(self) -> bytes:
        """Load existing key or generate new one"""
        if self.key_file.exists():
            with open(self.key_file, 'rb') as f:
                key = f.read()
            logger.debug("Loaded existing encryption key")
            return key
        
        # Generate new key
        key = Fernet.generate_key()
        with open(self.key_file, 'wb') as f:
            f.write(key)
        
        # Set restrictive permissions
        os.chmod(self.key_file, 0o600)
        
        logger.warning(f"Generated new encryption key: {self.key_file}")
        return key

    def save_secret(self, name: str, value: str) -> bool:
        """
        Save encrypted secret
        
        Args:
            name: Secret name
            value: Secret value
            
        Returns:
            True if successful
        """
        try:
            # Load existing secrets
            secrets = self._load_secrets()
            
            # Add/update secret
            secrets[name] = value
            
            # Encrypt and save
            encrypted = self.cipher.encrypt(json.dumps(secrets).encode())
            with open(self.secrets_file, 'wb') as f:
                f.write(encrypted)
            
            # Set restrictive permissions
            os.chmod(self.secrets_file, 0o600)
            
            logger.info(f"Secret '{name}' saved")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save secret: {e}")
            return False

    def get_secret(self, name: str) -> Optional[str]:
        """
        Retrieve decrypted secret
        
        Args:
            name: Secret name
            
        Returns:
            Secret value or None
        """
        try:
            secrets = self._load_secrets()
            return secrets.get(name)
        except Exception as e:
            logger.error(f"Failed to retrieve secret: {e}")
            return None

    def delete_secret(self, name: str) -> bool:
        """
        Delete a secret
        
        Args:
            name: Secret name
            
        Returns:
            True if deleted
        """
        try:
            secrets = self._load_secrets()
            if name in secrets:
                del secrets[name]
                
                if secrets:
                    encrypted = self.cipher.encrypt(json.dumps(secrets).encode())
                    with open(self.secrets_file, 'wb') as f:
                        f.write(encrypted)
                else:
                    self.secrets_file.unlink()
                
                logger.info(f"Secret '{name}' deleted")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete secret: {e}")
            return False

    def _load_secrets(self) -> Dict[str, str]:
        """Load and decrypt secrets"""
        if not self.secrets_file.exists():
            return {}
        
        with open(self.secrets_file, 'rb') as f:
            encrypted = f.read()
        
        decrypted = self.cipher.decrypt(encrypted)
        return json.loads(decrypted.decode())

    def list_secrets(self) -> list:
        """List secret names (not values)"""
        try:
            secrets = self._load_secrets()
            return list(secrets.keys())
        except Exception:
            return []

    def save_api_credentials(
        self,
        exchange: str,
        api_key: str,
        api_secret: str
    ) -> bool:
        """
        Save exchange API credentials
        
        Args:
            exchange: Exchange name
            api_key: API key
            api_secret: API secret
            
        Returns:
            True if successful
        """
        return self.save_secret(
            f"{exchange}_api_key",
            api_key
        ) and self.save_secret(
            f"{exchange}_api_secret",
            api_secret
        )

    def get_api_credentials(self, exchange: str) -> Optional[Dict[str, str]]:
        """
        Get exchange API credentials
        
        Args:
            exchange: Exchange name
            
        Returns:
            Credentials dict or None
        """
        api_key = self.get_secret(f"{exchange}_api_key")
        api_secret = self.get_secret(f"{exchange}_api_secret")
        
        if api_key and api_secret:
            return {'api_key': api_key, 'api_secret': api_secret}
        return None


class CredentialValidator:
    """Validate and check credentials"""

    @staticmethod
    def validate_api_key_format(api_key: str, exchange: str) -> bool:
        """
        Validate API key format for specific exchange
        
        Args:
            api_key: API key to validate
            exchange: Exchange name
            
        Returns:
            True if valid format
        """
        # Basic format checks
        if not api_key or len(api_key) < 10:
            return False
        
        # Exchange-specific checks
        if exchange.lower() == 'binance':
            return api_key.startswith('x') or api_key[0].isalpha()
        elif exchange.lower() == 'coinbase':
            return len(api_key) >= 32
        elif exchange.lower() == 'kraken':
            return len(api_key) >= 20
        
        return True

    @staticmethod
    def validate_wallet_address(address: str, currency: str = 'ETH') -> bool:
        """
        Validate wallet address format
        
        Args:
            address: Wallet address
            currency: Currency type
            
        Returns:
            True if valid format
        """
        if not address:
            return False
        
        if currency.upper() == 'ETH' or currency.upper() == 'USDT':
            # Ethereum address: 0x + 40 hex chars
            if not address.startswith('0x'):
                return False
            if len(address) != 42:
                return False
            try:
                int(address[2:], 16)
                return True
            except ValueError:
                return False
        
        elif currency.upper() == 'BTC':
            # Bitcoin address: various formats
            if address.startswith('1') or address.startswith('3'):
                return len(address) >= 26 and len(address) <= 35
            elif address.startswith('bc1'):
                return len(address) >= 42
            
            return False
        
        return True


def generate_secure_key() -> str:
    """Generate a secure random key"""
    import secrets
    return secrets.token_urlsafe(32)


def hash_sensitive_data(data: str) -> str:
    """Hash sensitive data for logging"""
    import hashlib
    return hashlib.sha256(data.encode()).hexdigest()[:8]


# Global secrets manager instance
_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """Get or create global secrets manager"""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager
