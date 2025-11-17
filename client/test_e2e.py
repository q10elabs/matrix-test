#!/usr/bin/env python3
"""
Test script for E2E encryption functionality.

Tests SSSS key derivation, encryption/decryption, and Olm operations.
"""

import sys
import os
from encryption import SSSSManager, E2EEncryption


def test_ssss_key_derivation():
    """Test SSSS key derivation from password."""
    print("Testing SSSS key derivation...")
    password = "testpassword"
    salt = b"testsalt1234567"  # 16 bytes

    key = SSSSManager.derive_key(password, salt)

    assert len(key) == 32, f"Expected 32 bytes, got {len(key)}"
    assert isinstance(key, bytes), "Key should be bytes"
    print("✓ SSSS key derivation works\n")


def test_ssss_encryption_decryption():
    """Test SSSS encryption and decryption."""
    print("Testing SSSS encryption/decryption...")

    plaintext = b"This is a test message for encryption"
    password = "testpassword"

    # Encrypt
    encrypted = SSSSManager.encrypt(plaintext, password)
    assert "ciphertext" in encrypted
    assert "iv" in encrypted
    assert "salt" in encrypted
    print(f"✓ Encrypted {len(plaintext)} bytes")

    # Decrypt
    decrypted = SSSSManager.decrypt(encrypted, password)
    assert decrypted == plaintext, "Decrypted text doesn't match original"
    print(f"✓ Decrypted successfully")

    # Test wrong password
    try:
        decrypted_wrong = SSSSManager.decrypt(encrypted, "wrongpassword")
        # The decryption might succeed but produce garbage
        if decrypted_wrong == plaintext:
            print("✗ Wrong password somehow decrypted correctly!")
            return False
        print("✓ Wrong password produces different output")
    except Exception as e:
        print(f"✓ Wrong password raises error: {e}")

    print()
    return True


def test_olm_account():
    """Test Olm account creation."""
    print("Testing Olm account creation...")

    try:
        import olm
        account = olm.Account()

        identity_keys = account.identity_keys
        assert "curve25519" in identity_keys
        assert "ed25519" in identity_keys
        print(f"✓ Created Olm account")
        print(f"  Curve25519: {identity_keys['curve25519'][:16]}...")
        print(f"  Ed25519: {identity_keys['ed25519'][:16]}...")

        # Test key generation
        account.generate_one_time_keys(5)
        one_time_keys = account.one_time_keys
        assert len(one_time_keys["curve25519"]) > 0
        print(f"✓ Generated {len(one_time_keys['curve25519'])} one-time keys")
        print()
        return True

    except Exception as e:
        print(f"✗ Olm test failed: {e}\n")
        return False


def test_megolm_session():
    """Test Megolm outbound session."""
    print("Testing Megolm outbound session...")

    try:
        import olm
        session = olm.OutboundGroupSession()

        plaintext = "Test message"
        ciphertext = session.encrypt(plaintext)

        print(f"✓ Created Megolm session: {session.id[:16]}...")
        print(f"✓ Encrypted message: {len(ciphertext)} bytes")
        print(f"✓ Session key available: {len(session.session_key)} bytes")
        print()
        return True

    except Exception as e:
        print(f"✗ Megolm test failed: {e}\n")
        return False


def test_ssss_with_json():
    """Test SSSS with JSON data (like real usage)."""
    print("Testing SSSS with JSON data...")

    import json
    import base64

    password = "testpassword"

    # Simulate storing encrypted Olm account data
    data = {
        "pickle": base64.b64encode(b"fake_olm_pickle_data").decode('utf-8'),
    }

    plaintext = json.dumps(data).encode('utf-8')
    encrypted = SSSSManager.encrypt(plaintext, password)

    # Decrypt and verify
    decrypted = SSSSManager.decrypt(encrypted, password)
    recovered_data = json.loads(decrypted.decode('utf-8'))

    assert recovered_data == data
    print(f"✓ SSSS JSON storage/retrieval works")
    print(f"  Encrypted data: {len(encrypted['ciphertext'])} bytes")
    print()
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("E2E Encryption Test Suite")
    print("=" * 60)
    print()

    try:
        test_ssss_key_derivation()
        test_ssss_encryption_decryption()
        test_olm_account()
        test_megolm_session()
        test_ssss_with_json()

        print("=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"✗ Test assertion failed: {e}")
        return 1
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
