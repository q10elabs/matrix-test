#!/usr/bin/env python3
"""
Receive and decrypt encrypted messages in the E2EE test room.

This program:
1. Loads bob's credentials and room config
2. Logs in with E2EE support
3. Processes pending events (accepts room invites)
4. Syncs continuously, waiting for and decrypting incoming messages
5. Logs all received messages with decryption status
"""

import sys
import json
import asyncio
import logging
import signal
from datetime import datetime
from pathlib import Path

from nio import (
    AsyncClient, ClientConfig, MatrixRoom, RoomMessageText,
    InviteEvent
)
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

# Global flag for graceful shutdown
shutdown_requested = False


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


async def process_pending_invites(client: AsyncClient) -> bool:
    """
    Process pending events and accept invitations.

    Args:
        client: AsyncClient instance (logged in)

    Returns:
        True if successful, False otherwise
    """
    logger.info("Processing pending events and invites...")

    try:
        sync_resp = await client.sync(timeout=0)

        if not isinstance(sync_resp, SyncResponse):
            logger.error(f"✗ Sync failed: {sync_resp}")
            return False

        # Log events
        joined_rooms = len(sync_resp.rooms.join)
        invited_rooms = len(sync_resp.rooms.invite)

        logger.info(f"✓ Sync completed")
        logger.info(f"  Joined rooms: {joined_rooms}")
        logger.info(f"  Invited rooms: {invited_rooms}")

        # Auto-join any invited rooms
        if invited_rooms > 0:
            logger.info("Accepting room invitations...")
            for room_id in sync_resp.rooms.invite.keys():
                try:
                    join_resp = await client.join(room_id)
                    logger.info(f"  ✓ Accepted invite to {room_id}")
                except Exception as e:
                    logger.error(f"  ✗ Failed to accept invite to {room_id}: {e}")

        return True

    except Exception as e:
        logger.error(f"✗ Exception during sync: {e}")
        return False


def message_callback(room: MatrixRoom, event: RoomMessageText) -> None:
    """
    Callback for handling received messages.

    Args:
        room: The room the message was received in
        event: The message event
    """
    # Determine if message was decrypted
    if hasattr(event, 'decrypted') and event.decrypted:
        status = "✓ DECRYPTED"
    else:
        status = "✗ NOT DECRYPTED"

    logger.info(f"[{room.display_name}] {status}")
    logger.info(f"  From: {room.user_name(event.sender)}")
    logger.info(f"  Time: {datetime.fromtimestamp(event.server_timestamp / 1000).isoformat()}")
    logger.info(f"  Body: {event.body}")


async def sync_with_callbacks(client: AsyncClient, room_id: str, duration: int = 30):
    """
    Sync continuously and wait for messages for a duration.

    Args:
        client: AsyncClient instance
        room_id: Expected room ID to monitor
        duration: Maximum seconds to wait for messages
    """
    logger.info(f"Waiting for messages in {room_id}...")
    logger.info(f"(Will wait up to {duration} seconds)")
    logger.info("")

    # Register message callback
    client.add_event_callback(message_callback, RoomMessageText)

    start_time = asyncio.get_event_loop().time()
    message_received = False

    while True:
        elapsed = asyncio.get_event_loop().time() - start_time

        if elapsed > duration:
            logger.info(f"Timeout reached ({duration}s)")
            break

        if shutdown_requested:
            logger.info("Shutdown requested")
            break

        try:
            sync_resp = await client.sync(timeout=5000)

            if isinstance(sync_resp, SyncResponse):
                # Check if we received any messages in our room
                if room_id in sync_resp.rooms.join:
                    room_data = sync_resp.rooms.join[room_id]
                    event_count = len(room_data.timeline.events)

                    if event_count > 0:
                        logger.debug(f"Received {event_count} event(s) in {room_id}")
                        message_received = True

            else:
                logger.error(f"Sync error: {sync_resp}")

        except asyncio.CancelledError:
            logger.info("Sync cancelled")
            break
        except Exception as e:
            logger.error(f"Sync exception: {e}")
            await asyncio.sleep(1)

    if not message_received:
        logger.info("⚠ No messages received during wait period")


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    global shutdown_requested
    logger.info("")
    logger.info("Shutdown signal received")
    shutdown_requested = True


async def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("Matrix E2EE Test: Receive Messages")
    logger.info("=" * 60)

    # Setup signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)

    # Load configurations
    logger.info("")
    user_config = load_user_config()
    if not user_config:
        return 1

    room_config = load_room_config()
    if not room_config:
        return 1

    # Get second user (receiver - bob)
    users = user_config["users"]
    if len(users) < 2:
        logger.error("✗ Need at least 2 users in configuration")
        return 1

    bob = users[1]  # Second user is receiver

    room_id = room_config["room_id"]

    logger.info("")
    logger.info(f"Receiver: {bob['user_id']}")
    logger.info(f"Room:     {room_id}")

    # Login as bob
    logger.info("")
    client, success = await login_with_encryption(bob)
    if not success:
        logger.error("✗ Failed to login as bob")
        return 1

    # Process pending invites
    logger.info("")
    if not await process_pending_invites(client):
        logger.error("✗ Failed to process pending invites")
        await client.close()
        return 1

    # Sync and wait for messages
    logger.info("")
    await sync_with_callbacks(client, room_id, duration=30)

    await client.close()

    logger.info("")
    logger.info("=" * 60)
    logger.info("✓ Receive complete!")
    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
