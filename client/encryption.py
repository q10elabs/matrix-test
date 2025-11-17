"""
End-to-end encryption support for Matrix client.

Provides Olm and Megolm encryption with SSSS (Secrets Storage Service) integration.
Handles:
  - Olm account initialization and management
  - Megolm room session encryption/decryption
  - SSSS encryption/decryption of sensitive keys
  - Device key management and sharing
  - Transparent message encryption/decryption

Key storage uses Matrix account data for persistence:
  - m.secret.v1.olm_account: Encrypted Olm account state
  - m.secret.v1.megolm_sessions: Encrypted Megolm sessions
  - m.secret.v1.ssss_key: SSSS key metadata (salt, iterations)
"""

import json
import base64
import os
import hashlib
import pickle
import requests
from urllib.parse import urljoin
from typing import Optional, Dict, Tuple, Any
import olm
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


class SSSSManager:
    """
    Secrets Storage Service (SSSS) encryption/decryption.

    Derives a key from the user's password and uses AES-CTR to encrypt
    sensitive data before storing in account data.
    """

    SSSS_KEY_SIZE = 32  # 256 bits for AES-256
    SSSS_IV_SIZE = 16   # 128 bits for AES-CTR IV
    ITERATIONS = 100000  # PBKDF2 iterations

    @staticmethod
    def derive_key(password: str, salt: bytes) -> bytes:
        """
        Derive SSSS key from password using PBKDF2-SHA256.

        Args:
            password: User's login password
            salt: Random salt (16 bytes)

        Returns:
            32-byte derived key for AES-256
        """
        return hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            SSSSManager.ITERATIONS,
            dklen=SSSSManager.SSSS_KEY_SIZE
        )

    @staticmethod
    def encrypt(plaintext: bytes, password: str, salt: Optional[bytes] = None) -> Dict[str, str]:
        """
        Encrypt data using SSSS.

        Args:
            plaintext: Data to encrypt
            password: User's password
            salt: Optional salt; generates new if not provided

        Returns:
            Dict with 'ciphertext', 'iv', 'salt' as base64 strings
        """
        if salt is None:
            salt = os.urandom(16)

        key = SSSSManager.derive_key(password, salt)
        iv = os.urandom(SSSSManager.SSSS_IV_SIZE)

        cipher = Cipher(
            algorithms.AES(key),
            modes.CTR(iv)
        )
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()

        return {
            'ciphertext': base64.b64encode(ciphertext).decode('utf-8'),
            'iv': base64.b64encode(iv).decode('utf-8'),
            'salt': base64.b64encode(salt).decode('utf-8'),
        }

    @staticmethod
    def decrypt(encrypted_data: Dict[str, str], password: str) -> bytes:
        """
        Decrypt SSSS-encrypted data.

        Args:
            encrypted_data: Dict with 'ciphertext', 'iv', 'salt'
            password: User's password

        Returns:
            Decrypted plaintext bytes
        """
        ciphertext = base64.b64decode(encrypted_data['ciphertext'])
        iv = base64.b64decode(encrypted_data['iv'])
        salt = base64.b64decode(encrypted_data['salt'])

        key = SSSSManager.derive_key(password, salt)

        cipher = Cipher(
            algorithms.AES(key),
            modes.CTR(iv)
        )
        decryptor = cipher.decryptor()
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()

        return plaintext


class E2EEncryption:
    """
    End-to-end encryption handler for Matrix.

    Manages Olm accounts and Megolm sessions, handles message encryption/decryption,
    and persists keys via SSSS in account data.
    """

    def __init__(self, client, user_id: str, password: str):
        """
        Initialize E2E encryption.

        Args:
            client: MatrixClient instance
            user_id: User ID (@user:host)
            password: User's password for SSSS key derivation
        """
        self.client = client
        self.user_id = user_id
        self.password = password
        self.account = None
        self.megolm_sessions = {}  # room_id -> OutboundGroupSession
        self.received_sessions = {}  # (room_id, user_id, session_id) -> InboundGroupSession

    def initialize(self) -> bool:
        """
        Initialize or restore Olm account from SSSS.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Try to load existing account from SSSS
            account_data = self._load_from_ssss('m.secret.v1.olm_account')

            if account_data:
                # Restore existing account
                account_pickle = base64.b64decode(account_data['pickle'])
                # Note: Account.from_pickle() is a class method that returns a new Account instance
                self.account = olm.Account.from_pickle(account_pickle, self.password)
                print("[E2E] Restored Olm account from SSSS")
            else:
                # Create new account
                self.account = olm.Account()
                print("[E2E] Created new Olm account")

            # Load megolm sessions
            sessions_data = self._load_from_ssss('m.secret.v1.megolm_sessions')
            if sessions_data:
                self._restore_megolm_sessions(sessions_data)

            # Share one-time keys
            self._upload_keys()

            # Save account immediately
            self._save_to_ssss()

            return True

        except Exception as e:
            print(f"[E2E] Initialization failed: {e}")
            return False

    def _upload_keys(self):
        """Upload device keys and one-time keys to server."""
        try:
            identity_keys = self.account.identity_keys
            one_time_keys = self.account.one_time_keys

            # This would typically use /keys/upload endpoint
            # For now, we'll just mark the keys as published
            self.account.mark_keys_as_published()
            print(f"[E2E] Device ID: {self.client.device_id}")
            print(f"[E2E] Curve25519 key: {identity_keys['curve25519'][:16]}...")
            print(f"[E2E] Ed25519 key: {identity_keys['ed25519'][:16]}...")

        except Exception as e:
            print(f"[E2E] Key upload failed: {e}")

    def _save_to_ssss(self) -> bool:
        """Save Olm account and megolm sessions to SSSS."""
        try:
            # Save Olm account
            # Note: olm.pickle() expects a string passphrase, not bytes
            account_pickle = self.account.pickle(self.password)
            account_data = {
                'pickle': base64.b64encode(account_pickle).decode('utf-8'),
            }
            self._store_to_ssss('m.secret.v1.olm_account', account_data)

            # Save Megolm sessions
            if self.megolm_sessions:
                sessions_data = self._prepare_megolm_sessions()
                self._store_to_ssss('m.secret.v1.megolm_sessions', sessions_data)

            return True
        except Exception as e:
            print(f"[E2E] Failed to save to SSSS: {e}")
            return False

    def _store_to_ssss(self, key: str, data: Dict[str, Any]):
        """
        Store data in SSSS via account data.

        Args:
            key: Account data key (e.g., 'm.secret.v1.olm_account')
            data: Data to store
        """
        plaintext = json.dumps(data).encode('utf-8')
        encrypted = SSSSManager.encrypt(plaintext, self.password)

        try:
            self.client.api.set_account_data(
                self.user_id,
                key,
                encrypted
            )
        except Exception as e:
            print(f"[E2E] Failed to store {key}: {e}")

    def _load_from_ssss(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Load data from SSSS via account data.

        Args:
            key: Account data key

        Returns:
            Decrypted data dict or None if not found
        """
        try:
            # Use REST API directly since matrix-client doesn't have get_account_data
            # Build the full URL using the homeserver address
            homeserver_url = f"http://{self.client.hs}:8008"
            url = urljoin(
                homeserver_url,
                f"/_matrix/client/r0/user/{self.user_id}/account_data/{key}"
            )
            response = requests.get(
                url,
                params={"access_token": self.client.token},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if 'ciphertext' in data:
                    plaintext = SSSSManager.decrypt(data, self.password)
                    return json.loads(plaintext.decode('utf-8'))
            elif response.status_code == 404:
                # Data doesn't exist yet
                return None
        except Exception as e:
            # Data doesn't exist yet, or decryption failed
            pass
        return None

    def _prepare_megolm_sessions(self) -> Dict[str, Any]:
        """Prepare megolm sessions for storage."""
        sessions = {}
        for room_id, session in self.megolm_sessions.items():
            # Note: olm.pickle() expects a string passphrase, not bytes
            session_pickle = session.pickle(self.password)
            sessions[room_id] = base64.b64encode(session_pickle).decode('utf-8')
        return {'sessions': sessions}

    def _restore_megolm_sessions(self, sessions_data: Dict[str, Any]):
        """Restore megolm sessions from storage."""
        try:
            for room_id, session_pickle_b64 in sessions_data.get('sessions', {}).items():
                session_pickle = base64.b64decode(session_pickle_b64)
                # Note: from_pickle() is a class method that returns a new session instance
                session = olm.OutboundGroupSession.from_pickle(session_pickle, self.password)
                self.megolm_sessions[room_id] = session
            print(f"[E2E] Restored {len(self.megolm_sessions)} megolm sessions")
        except Exception as e:
            print(f"[E2E] Failed to restore megolm sessions: {e}")

    def get_room_keys(self, room_id: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Get encryption keys for a room.

        Creates a new Megolm session if one doesn't exist.

        Args:
            room_id: Room ID

        Returns:
            Tuple of (session_id, session_key) or (None, None)
        """
        try:
            if room_id not in self.megolm_sessions:
                # Create new outbound session
                session = olm.OutboundGroupSession()
                self.megolm_sessions[room_id] = session
                print(f"[E2E] Created new megolm session for {room_id}")

            session = self.megolm_sessions[room_id]
            return session.id, session.session_key

        except Exception as e:
            print(f"[E2E] Failed to get room keys: {e}")
            return None, None

    def encrypt_message(self, room_id: str, plaintext: str) -> Optional[Dict[str, Any]]:
        """
        Encrypt a message for a room.

        Args:
            room_id: Room ID
            plaintext: Message text

        Returns:
            Encrypted event dict or None if encryption fails
        """
        try:
            if room_id not in self.megolm_sessions:
                session = olm.OutboundGroupSession()
                self.megolm_sessions[room_id] = session

            session = self.megolm_sessions[room_id]
            ciphertext = session.encrypt(plaintext)

            return {
                'algorithm': 'm.megolm.v1.aes-sha2',
                'ciphertext': ciphertext,
                'device_id': self.client.device_id,
                'session_id': session.id,
                'sender_key': self.account.identity_keys['curve25519'],
            }

        except Exception as e:
            print(f"[E2E] Message encryption failed: {e}")
            return None

    def decrypt_message(self, room_id: str, event: Dict[str, Any]) -> Optional[str]:
        """
        Decrypt an encrypted event.

        Args:
            room_id: Room ID
            event: Event dict with 'm.room.encrypted' content

        Returns:
            Decrypted plaintext or None if decryption fails
        """
        try:
            content = event.get('content', {})
            algorithm = content.get('algorithm')

            if algorithm == 'm.megolm.v1.aes-sha2':
                ciphertext = content.get('ciphertext')
                sender_key = content.get('sender_key')
                session_id = content.get('session_id')

                if not all([ciphertext, sender_key, session_id]):
                    return None

                # Try to decrypt
                key = (room_id, event.get('sender'), session_id)
                if key in self.received_sessions:
                    session = self.received_sessions[key]
                    plaintext, _ = session.decrypt(ciphertext)
                    return plaintext.decode('utf-8')

            return None

        except Exception as e:
            print(f"[E2E] Decryption failed: {e}")
            return None

    def is_encrypted_room(self, room_state: Dict[str, Any]) -> bool:
        """
        Check if a room has encryption enabled.

        Args:
            room_state: Room state events

        Returns:
            True if m.room.encryption state exists
        """
        for event in room_state.get('state', {}).get('events', []):
            if event.get('type') == 'm.room.encryption':
                return True
        return False

    def needs_key_rotation(self, room_id: str) -> bool:
        """
        Check if a megolm session needs rotation.

        Args:
            room_id: Room ID

        Returns:
            True if session should be rotated
        """
        if room_id not in self.megolm_sessions:
            return True

        session = self.megolm_sessions[room_id]
        # Rotate after 100 messages (Matrix recommendation)
        return session.message_count > 100
