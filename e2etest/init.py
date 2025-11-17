#!/usr/bin/env python3
"""
Initialize E2EE test environment by registering users and setting up encryption keys.

This program:
1. Registers two users (alice and bob) with the Matrix homeserver
2. Initializes E2EE encryption for each user (Olm account setup)
3. Uploads device keys and one-time keys to the server
4. Persists user credentials and device IDs to userconfig.json

The userconfig.json file is used by setup.py, send.py, and recv.py.
"""

import sys
import json
import asyncio
import hashlib
import logging
import random
import string
from datetime import datetime
from pathlib import Path

from nio import AsyncClient, ClientConfig
from nio.responses import RegisterResponse, LoginResponse
from nio.crypto import Olm

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Configuration
SERVER_URL = "http://localhost:8008"
SCRIPT_DIR = Path(__file__).parent.absolute()
STORE_PATH = SCRIPT_DIR / "nio_store"
CONFIG_FILE = SCRIPT_DIR / "userconfig.json"


def generate_random_username() -> str:
    """Generate a random username."""
    # Generate format: user_XXXXX where X is random alphanumeric
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
    return f"user_{random_suffix}"


def derive_password(username: str) -> str:
    """Derive password from username using MD5 hash."""
    return hashlib.md5(username.encode()).hexdigest()


async def register_user(username: str) -> tuple[bool, dict]:
    """
    Register a user and return their details.

    Args:
        username: Username to register

    Returns:
        Tuple of (success: bool, user_info: dict)
    """
    logger.info(f"Registering user: {username}")

    password = derive_password(username)
    user_id = f"@{username}:localhost"

    # Create client with encryption support
    config = ClientConfig()
    client = AsyncClient(SERVER_URL, user_id, config=config)

    try:
        # Register user
        resp = await client.register(username, password, device_name="E2E Test Device")

        if isinstance(resp, RegisterResponse):
            device_id = resp.device_id
            user_info = {
                "username": username,
                "password": password,
                "user_id": resp.user_id,
                "device_id": device_id,
                "registered_at": datetime.now().isoformat()
            }
            logger.info(f"✓ Registered {username}: {resp.user_id}, device: {device_id}")
            return True, user_info
        else:
            logger.error(f"✗ Registration failed for {username}: {resp}")
            return False, {}

    except Exception as e:
        logger.error(f"✗ Exception during registration for {username}: {e}")
        return False, {}
    finally:
        await client.close()


async def setup_encryption_keys(user_info: dict) -> bool:
    """
    Setup E2EE encryption keys for a user.

    Args:
        user_info: User info dict from registration

    Returns:
        True if successful, False otherwise
    """
    username = user_info["username"]
    user_id = user_info["user_id"]
    password = user_info["password"]
    device_id = user_info["device_id"]

    logger.info(f"Setting up E2EE keys for {username}")

    # Create store directory if it doesn't exist
    STORE_PATH.mkdir(parents=True, exist_ok=True)

    # Create client with encryption enabled
    config = ClientConfig()
    client = AsyncClient(
        SERVER_URL,
        user_id,
        device_id=device_id,
        store_path=str(STORE_PATH),
        config=config
    )

    try:
        # Login with the registered user
        resp = await client.login(password)

        if not isinstance(resp, LoginResponse):
            logger.error(f"✗ Login failed for {username}: {resp}")
            return False

        logger.info(f"✓ Logged in as {username} with device {device_id}")

        # Ensure encryption is loaded
        if not client.olm:
            logger.error(f"✗ Olm not initialized for {username}")
            await client.close()
            return False

        # Share keys (upload device keys and one-time keys)
        logger.info(f"Uploading encryption keys for {username}")
        keys_to_upload = client.olm.share_keys()

        if not keys_to_upload:
            logger.warning(f"⚠ No keys to upload for {username}")
        else:
            logger.info(f"✓ Prepared keys for upload: {list(keys_to_upload.keys())}")

            # Actually upload keys to server
            # The client.keys_upload() method automatically uses olm.share_keys()
            upload_resp = await client.keys_upload()

            logger.info(f"✓ Uploaded encryption keys for {username}")
            logger.debug(f"  Upload response: {upload_resp}")

        # Save Olm state
        client.olm.save_account()
        logger.info(f"✓ Saved Olm state for {username}")

        await client.close()
        return True

    except Exception as e:
        logger.error(f"✗ Exception setting up encryption for {username}: {e}")
        await client.close()
        return False


def save_user_config(users: list[dict]) -> bool:
    """
    Save user configuration to JSON file.

    Args:
        users: List of user info dicts

    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Saving configuration to {CONFIG_FILE}")

    try:
        config = {"users": users}
        with open(str(CONFIG_FILE), "w") as f:
            json.dump(config, f, indent=2)
        logger.info(f"✓ Saved {len(users)} users to {CONFIG_FILE}")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to save config: {e}")
        return False


async def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("Matrix E2EE Test: User Registration and Key Setup")
    logger.info("=" * 60)

    # Generate random usernames
    usernames = [generate_random_username(), generate_random_username()]
    logger.info(f"Generated usernames: {usernames}")

    users = []

    # Register all users
    for username in usernames:
        success, user_info = await register_user(username)
        if not success:
            logger.error(f"Failed to register {username}, aborting")
            return 1
        users.append(user_info)

    logger.info("")
    logger.info("Registered users:")
    for u in users:
        logger.info(f"  - {u['username']}: {u['user_id']}")

    # Setup encryption keys for each user
    logger.info("")
    logger.info("Setting up encryption keys...")
    for user_info in users:
        success = await setup_encryption_keys(user_info)
        if not success:
            logger.error(f"Failed to setup encryption for {user_info['username']}, aborting")
            return 1

    logger.info("")
    logger.info("All users have encryption keys configured")

    # Save configuration
    logger.info("")
    if not save_user_config(users):
        logger.error("Failed to save user configuration")
        return 1

    logger.info("")
    logger.info("=" * 60)
    logger.info("✓ Initialization complete!")
    logger.info("=" * 60)
    logger.info(f"Configuration saved to: {CONFIG_FILE}")
    logger.info("")
    logger.info("Next steps:")
    logger.info("  1. Run: python setup.py")
    logger.info("  2. In another terminal: python send.py")
    logger.info("  3. In another terminal: python recv.py")

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
