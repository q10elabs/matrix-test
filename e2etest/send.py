#!/usr/bin/env python3
"""
Send an encrypted message in the E2EE test room.

This program:
1. Loads alice's credentials and room config
2. Logs in with E2EE support
3. Processes pending events (syncs)
4. Sends an encrypted message to the test room
5. Waits briefly to process further events
"""

import sys
import json
import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path

from nio import AsyncClient, ClientConfig, MatrixRoom, RoomMessageText
from nio.responses import LoginResponse, SyncResponse, RoomSendResponse, JoinResponse

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


def load_user_config() -> dict:
    """Load user configuration from JSON file."""
    logger.info(f"Loading configuration from {USERCONFIG_FILE}")
    try:
        with open(str(USERCONFIG_FILE), "r") as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        logger.error(f"✗ {USERCONFIG_FILE} not found. Run init.py first.")
        return None
    except Exception as e:
        logger.error(f"✗ Failed to load config: {e}")
        return None


def load_room_config() -> dict:
    """Load room configuration from JSON file."""
    logger.info(f"Loading room config from {ROOMCONFIG_FILE}")
    try:
        with open(str(ROOMCONFIG_FILE), "r") as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        logger.error(f"✗ {ROOMCONFIG_FILE} not found. Run setup.py first.")
        return None
    except Exception as e:
        logger.error(f"✗ Failed to load room config: {e}")
        return None


def get_user_by_name(config: dict, username: str) -> dict:
    """Get user info by username."""
    for user in config["users"]:
        if user["username"] == username:
            return user
    return None


async def login_with_encryption(user_info: dict) -> tuple[AsyncClient, bool]:
    """Login as a user with E2EE support."""
    username = user_info["username"]
    user_id = user_info["user_id"]
    password = user_info["password"]
    device_id = user_info["device_id"]

    logger.info(f"Logging in as {username} (device: {device_id})")

    config = ClientConfig()
    client = AsyncClient(
        SERVER_URL,
        user_id,
        device_id=device_id,
        store_path=str(STORE_PATH),
        config=config
    )

    try:
        resp = await client.login(password)

        if not isinstance(resp, LoginResponse):
            logger.error(f"✗ Login failed: {resp}")
            await client.close()
            return None, False

        logger.info(f"✓ Logged in as {username}")
        return client, True

    except Exception as e:
        logger.error(f"✗ Exception during login: {e}")
        await client.close()
        return None, False


async def process_pending_events(client: AsyncClient) -> bool:
    """
    Process pending events and sync with server.

    Args:
        client: AsyncClient instance (logged in)

    Returns:
        True if successful, False otherwise
    """
    logger.info("Processing pending events...")

    try:
        sync_resp = await client.sync(timeout=0)

        if not isinstance(sync_resp, SyncResponse):
            logger.error(f"✗ Sync failed: {sync_resp}")
            return False

        # Log any events received
        joined_rooms = len(sync_resp.rooms.join)
        invited_rooms = len(sync_resp.rooms.invite)

        logger.info(f"✓ Sync completed")
        logger.info(f"  Joined rooms: {joined_rooms}")
        logger.info(f"  Invited rooms: {invited_rooms}")

        # Auto-join any invited rooms
        if invited_rooms > 0:
            logger.info("Auto-joining invited rooms...")
            for room_id in sync_resp.rooms.invite.keys():
                try:
                    join_resp = await client.join(room_id)
                    logger.info(f"  Joined {room_id}")
                except Exception as e:
                    logger.error(f"  Failed to join {room_id}: {e}")

        return True

    except Exception as e:
        logger.error(f"✗ Exception during sync: {e}")
        return False


async def send_encrypted_message(client: AsyncClient, room_id: str, message: str) -> bool:
    """
    Send an encrypted message to a room.

    Args:
        client: AsyncClient instance (logged in)
        room_id: Room ID to send to
        message: Message text

    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Sending encrypted message to {room_id}")
    logger.info(f"Message: {message}")

    try:
        resp = await client.room_send(
            room_id=room_id,
            message_type="m.room.message",
            content={
                "msgtype": "m.text",
                "body": message
            }
        )

        if isinstance(resp, RoomSendResponse):
            logger.info(f"✓ Message sent successfully")
            logger.info(f"  Event ID: {resp.event_id}")
            return True
        else:
            logger.error(f"✗ Failed to send message: {resp}")
            return False

    except Exception as e:
        logger.error(f"✗ Exception sending message: {e}")
        return False


async def wait_for_events(client: AsyncClient, duration: int = 5):
    """
    Wait and process further events for a duration.

    Args:
        client: AsyncClient instance
        duration: How many seconds to wait
    """
    logger.info(f"Waiting {duration} seconds to process further events...")

    end_time = time.time() + duration
    while time.time() < end_time:
        try:
            sync_resp = await client.sync(timeout=1000)

            if isinstance(sync_resp, SyncResponse):
                # Count events in joined rooms
                total_events = 0
                for room_id, room_data in sync_resp.rooms.join.items():
                    total_events += len(room_data.timeline.events)

                if total_events > 0:
                    logger.info(f"Received {total_events} events from server")

        except Exception as e:
            logger.debug(f"Sync error (expected during wait): {e}")

    logger.info("Wait period complete")


async def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("Matrix E2EE Test: Send Message")
    logger.info("=" * 60)

    # Load configurations
    logger.info("")
    user_config = load_user_config()
    if not user_config:
        return 1

    room_config = load_room_config()
    if not room_config:
        return 1

    # Get first user (sender - alice)
    users = user_config["users"]
    if len(users) < 1:
        logger.error("✗ No users in configuration")
        return 1

    alice = users[0]  # First user is sender

    room_id = room_config["room_id"]

    logger.info("")
    logger.info(f"Sender: {alice['user_id']}")
    logger.info(f"Room:   {room_id}")

    # Login as alice
    logger.info("")
    client, success = await login_with_encryption(alice)
    if not success:
        logger.error("✗ Failed to login as alice")
        return 1

    # Process pending events
    logger.info("")
    if not await process_pending_events(client):
        logger.error("✗ Failed to process pending events")
        await client.close()
        return 1

    # Join the room if not already in it
    logger.info("")
    logger.info(f"Joining room {room_id}")
    try:
        join_resp = await client.join(room_id)
        logger.info(f"✓ Joined room")
    except Exception as e:
        logger.error(f"✗ Failed to join room: {e}")
        await client.close()
        return 1

    # Sync again to load room state properly
    logger.info("Syncing after room join...")
    try:
        await client.sync(timeout=0)
        logger.info("✓ Synced room state")
    except Exception as e:
        logger.error(f"⚠ Failed to sync after join: {e}")

    # For E2E testing: mark all devices in the room as trusted
    logger.info("Marking devices as trusted for E2E encryption...")
    try:
        for user_id, devices in client.olm.device_store.items():
            for device_id, device in devices.items():
                if user_id != alice["user_id"]:  # Trust other users' devices
                    client.olm.verify_device(device)
                    logger.debug(f"  Marked {device_id} from {user_id} as trusted")
    except Exception as e:
        logger.warning(f"⚠ Failed to verify devices: {e}")

    # Send encrypted message
    logger.info("")
    message = f"Hello from alice at {datetime.now().isoformat()}!"
    if not await send_encrypted_message(client, room_id, message):
        logger.error("✗ Failed to send message")
        await client.close()
        return 1

    # Wait for further events
    logger.info("")
    await wait_for_events(client, duration=5)

    await client.close()

    logger.info("")
    logger.info("=" * 60)
    logger.info("✓ Send complete!")
    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
