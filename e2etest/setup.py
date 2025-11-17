#!/usr/bin/env python3
"""
Setup E2EE test by creating an encrypted room and inviting the second user.

This program:
1. Loads alice's credentials from userconfig.json
2. Logs in with E2EE support
3. Creates a new room with encryption enabled
4. Invites bob to the room
5. Saves room details to roomconfig.json

The roomconfig.json file is used by send.py and recv.py.
"""

import sys
import json
import asyncio
import logging
import random
import string
from datetime import datetime
from pathlib import Path

from nio import AsyncClient, ClientConfig, RoomCreateResponse, RoomInviteResponse
from nio.responses import LoginResponse, SyncResponse

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
USERCONFIG_FILE = SCRIPT_DIR / "userconfig.json"
ROOMCONFIG_FILE = SCRIPT_DIR / "roomconfig.json"


def generate_random_room_name() -> str:
    """Generate a random room name."""
    # Generate format: room_XXXXX where X is random alphanumeric
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
    return f"room_{random_suffix}"


def load_user_config() -> dict:
    """
    Load user configuration from JSON file.

    Returns:
        Dict with users list, or None on error
    """
    logger.info(f"Loading configuration from {USERCONFIG_FILE}")

    try:
        with open(str(USERCONFIG_FILE), "r") as f:
            config = json.load(f)
        logger.info(f"✓ Loaded {len(config['users'])} users")
        return config
    except FileNotFoundError:
        logger.error(f"✗ {USERCONFIG_FILE} not found. Run init.py first.")
        return None
    except Exception as e:
        logger.error(f"✗ Failed to load config: {e}")
        return None


def get_user_by_name(config: dict, username: str) -> dict:
    """Get user info by username."""
    for user in config["users"]:
        if user["username"] == username:
            return user
    return None


async def login_with_encryption(user_info: dict) -> tuple[AsyncClient, bool]:
    """
    Login as a user with E2EE support.

    Args:
        user_info: User info dict from config

    Returns:
        Tuple of (client: AsyncClient or None, success: bool)
    """
    username = user_info["username"]
    user_id = user_info["user_id"]
    password = user_info["password"]
    device_id = user_info["device_id"]

    logger.info(f"Logging in as {username} (device: {device_id})")

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
        # Login
        resp = await client.login(password)

        if not isinstance(resp, LoginResponse):
            logger.error(f"✗ Login failed: {resp}")
            await client.close()
            return None, False

        logger.info(f"✓ Logged in as {username}")

        # Perform initial sync to load encryption state
        logger.info("Performing initial sync...")
        sync_resp = await client.sync(timeout=0)

        if not isinstance(sync_resp, SyncResponse):
            logger.error(f"✗ Sync failed: {sync_resp}")
            await client.close()
            return None, False

        logger.info(f"✓ Synced successfully")
        return client, True

    except Exception as e:
        logger.error(f"✗ Exception during login: {e}")
        await client.close()
        return None, False


async def create_encrypted_room(client: AsyncClient, room_name: str) -> tuple[str, bool]:
    """
    Create a new room with encryption enabled.

    Args:
        client: AsyncClient instance (logged in)
        room_name: Name for the new room

    Returns:
        Tuple of (room_id: str, success: bool)
    """
    logger.info(f"Creating encrypted room: {room_name}")

    try:
        # Create room with encryption enabled
        resp = await client.room_create(
            name=room_name,
            initial_state=[
                {
                    "type": "m.room.encryption",
                    "content": {"algorithm": "m.megolm.v1.aes-sha2"}
                }
            ]
        )

        if not isinstance(resp, RoomCreateResponse):
            logger.error(f"✗ Failed to create room: {resp}")
            return None, False

        room_id = resp.room_id
        logger.info(f"✓ Created encrypted room: {room_id}")
        return room_id, True

    except Exception as e:
        logger.error(f"✗ Exception creating room: {e}")
        return None, False


async def invite_user_to_room(client: AsyncClient, room_id: str, invitee_id: str) -> bool:
    """
    Invite a user to a room.

    Args:
        client: AsyncClient instance (logged in)
        room_id: Room ID to invite to
        invitee_id: User ID to invite

    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Inviting {invitee_id} to {room_id}")

    try:
        resp = await client.room_invite(room_id, invitee_id)

        if not isinstance(resp, RoomInviteResponse):
            logger.error(f"✗ Failed to invite {invitee_id}: {resp}")
            return False

        logger.info(f"✓ Invited {invitee_id} to {room_id}")
        return True

    except Exception as e:
        logger.error(f"✗ Exception inviting user: {e}")
        return False


def save_room_config(room_id: str, room_name: str) -> bool:
    """
    Save room configuration to JSON file.

    Args:
        room_id: Room ID
        room_name: Room name

    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Saving room configuration to {ROOMCONFIG_FILE}")

    try:
        config = {
            "room_id": room_id,
            "room_name": room_name,
            "created_at": datetime.now().isoformat(),
            "encrypted": True
        }
        with open(str(ROOMCONFIG_FILE), "w") as f:
            json.dump(config, f, indent=2)
        logger.info(f"✓ Saved room config to {ROOMCONFIG_FILE}")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to save room config: {e}")
        return False


async def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("Matrix E2EE Test: Room Setup")
    logger.info("=" * 60)

    # Load user config
    logger.info("")
    config = load_user_config()
    if not config:
        return 1

    # Get first user (sender) and second user (receiver)
    users = config["users"]
    if len(users) < 2:
        logger.error("✗ Need at least 2 users in configuration")
        return 1

    alice = users[0]  # First user is sender
    bob = users[1]    # Second user is receiver

    logger.info("")
    logger.info(f"Sender (alice): {alice['user_id']} ({alice['username']})")
    logger.info(f"Receiver (bob): {bob['user_id']} ({bob['username']})")

    # Login as alice
    logger.info("")
    client, success = await login_with_encryption(alice)
    if not success:
        logger.error("✗ Failed to login as alice")
        return 1

    # Generate random room name and create encrypted room
    logger.info("")
    room_name = generate_random_room_name()
    logger.info(f"Generated room name: {room_name}")
    room_id, success = await create_encrypted_room(client, room_name)
    if not success:
        logger.error("✗ Failed to create room")
        await client.close()
        return 1

    # Invite bob
    logger.info("")
    success = await invite_user_to_room(client, room_id, bob["user_id"])
    if not success:
        logger.error("✗ Failed to invite bob")
        await client.close()
        return 1

    # Save room config
    logger.info("")
    if not save_room_config(room_id, room_name):
        logger.error("✗ Failed to save room config")
        await client.close()
        return 1

    await client.close()

    logger.info("")
    logger.info("=" * 60)
    logger.info("✓ Setup complete!")
    logger.info("=" * 60)
    logger.info(f"Room ID: {room_id}")
    logger.info(f"Configuration saved to: {ROOMCONFIG_FILE}")
    logger.info("")
    logger.info("Next steps:")
    logger.info("  1. In one terminal: python send.py")
    logger.info("  2. In another terminal: python recv.py")

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
