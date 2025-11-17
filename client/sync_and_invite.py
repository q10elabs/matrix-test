#!/usr/bin/env python3
"""
Synchronize Matrix events, accept pending invites, and send messages with E2E encryption.

This program logs in a user, processes incoming events from the Matrix sync protocol,
automatically accepts pending invites, and optionally sends a message to a specified room.
Supports end-to-end encryption via matrix-nio's built-in E2E capabilities.

The sync cursor is persisted server-side using the Matrix account data API, allowing
the client to resume from where it left off on subsequent runs without reprocessing events.

Encryption is handled transparently using matrix-nio's Olm integration when the library
is built with E2E support.

Examples:
  python sync_and_invite.py alice
  python sync_and_invite.py alice '#myroom:localhost'
  python sync_and_invite.py alice '#myroom:localhost' 'Hello from sync_and_invite!'
  python sync_and_invite.py alice '#myroom:localhost' 'Hello' --no-save-token
  python sync_and_invite.py alice --no-load-token
"""

import sys
import hashlib
import json
import asyncio
import argparse
from nio import AsyncClient
from nio.responses import (
    LoginResponse, SyncResponse, JoinResponse, RoomSendResponse
)


async def login_user(username):
    """
    Login to the Matrix homeserver and return an AsyncClient.

    Args:
        username: The username (e.g., alice) or full user ID format (@alice:localhost)

    Returns:
        Tuple of (success: bool, (client: AsyncClient, user_id: str, password: str) or message: str)
    """
    server_url = "http://localhost:8008"

    # Extract the plain username for password derivation
    if username.startswith("@") and ":" in username:
        plain_username = username[1:username.index(":")]
        user_id_to_try = username
    else:
        plain_username = username
        user_id_to_try = f"@{username}:localhost"

    # Derive password from the plain username as MD5 hash
    password = hashlib.md5(plain_username.encode()).hexdigest()

    # Create async client
    client = AsyncClient(server_url, user_id_to_try)

    try:
        # Login
        resp = await client.login(password)

        if isinstance(resp, LoginResponse):
            user_id = resp.user_id
            return True, (client, user_id, password)
        else:
            # Handle error response
            error_msg = str(resp)
            await client.close()
            return False, f"Login failed: {error_msg}"

    except Exception as e:
        await client.close()
        return False, f"Error during login: {str(e)}"


async def get_sync_token_from_server(client, user_id):
    """
    Retrieve the stored sync token from server account data.

    Uses the Matrix account data API to store/retrieve per-user data
    server-side, allowing sync resumption across client runs.

    Args:
        client: The AsyncClient instance
        user_id: The user ID (@user:host format)

    Returns:
        The sync token string, or None if not found
    """
    try:
        # Build the path for user account data
        path = f"/_matrix/client/r0/user/{user_id}/account_data/org.matrix.sync_token?access_token={client.access_token}"

        # GET the account data
        resp = await client.send("GET", path)

        if resp.status == 200:
            data = json.loads(await resp.text())
            return data.get("sync_token")

        return None
    except Exception as e:
        print(f"Warning: Failed to retrieve sync token: {str(e)}")
        return None


async def store_sync_token_to_server(client, user_id, sync_token):
    """
    Store the sync token to server account data.

    Uses the Matrix account data API to store per-user data server-side.
    This allows the client to resume syncing from the last known position
    on subsequent runs.

    Args:
        client: The AsyncClient instance
        user_id: The user ID (@user:host format)
        sync_token: The sync token to store

    Returns:
        True if successful, False otherwise
    """
    try:
        # Build the path for user account data
        path = f"/_matrix/client/r0/user/{user_id}/account_data/org.matrix.sync_token?access_token={client.access_token}"

        # PUT the account data
        data = {"sync_token": sync_token}
        resp = await client.send("PUT", path, data=json.dumps(data))

        return resp.status == 200
    except Exception as e:
        print(f"Warning: Failed to store sync token: {str(e)}")
        return False


async def accept_pending_invites(client, invited_rooms):
    """
    Accept all pending room invitations.

    Args:
        client: The AsyncClient instance
        invited_rooms: Dict of room_id -> room_data from sync response

    Returns:
        List of room IDs that were joined
    """
    joined = []

    for room_id in invited_rooms.keys():
        try:
            resp = await client.join(room_id)
            if isinstance(resp, JoinResponse):
                print(f"Accepted invite: {room_id}")
                joined.append(room_id)
            else:
                print(f"Error accepting invite for {room_id}: {str(resp)}")
        except Exception as e:
            print(f"Error accepting invite for {room_id}: {str(e)}")

    return joined


def process_events(sync_resp):
    """
    Extract and format events from sync response.

    Args:
        sync_resp: The SyncResponse object

    Returns:
        Dict with event summaries
    """
    events_summary = {
        "join": {},
        "invite": {},
        "leave": {}
    }

    # Process joined rooms
    for room_id, room_data in sync_resp.rooms.join.items():
        events = room_data.timeline.events
        if events:
            event_dicts = []
            for event in events:
                event_dict = {}

                # Get event type
                if hasattr(event, 'type'):
                    event_dict["type"] = event.type

                # Common attributes
                for attr in ['sender', 'event_id', 'server_timestamp']:
                    if hasattr(event, attr):
                        event_dict[attr] = getattr(event, attr)

                # Content-based attributes
                if hasattr(event, 'body'):
                    event_dict["body"] = event.body
                if hasattr(event, 'content'):
                    event_dict["content"] = event.content
                if hasattr(event, 'membership'):
                    event_dict["membership"] = event.membership

                if event_dict:
                    event_dicts.append(event_dict)

            events_summary["join"][room_id] = {
                "count": len(event_dicts),
                "events": event_dicts
            }

    # Process invited rooms
    for room_id, room_data in sync_resp.rooms.invite.items():
        if room_data.invite_state:
            event_dicts = []
            for event in room_data.invite_state:
                if isinstance(event, dict):
                    event_dicts.append(event)

            if event_dicts:
                events_summary["invite"][room_id] = {
                    "count": len(event_dicts),
                    "events": event_dicts
                }

    # Process left rooms
    for room_id, room_data in sync_resp.rooms.leave.items():
        events = room_data.timeline.events
        if events:
            event_dicts = []
            for event in events:
                event_dict = {}

                if hasattr(event, 'type'):
                    event_dict["type"] = event.type

                for attr in ['sender', 'event_id', 'server_timestamp']:
                    if hasattr(event, attr):
                        event_dict[attr] = getattr(event, attr)

                if hasattr(event, 'body'):
                    event_dict["body"] = event.body
                if hasattr(event, 'content'):
                    event_dict["content"] = event.content

                if event_dict:
                    event_dicts.append(event_dict)

            if event_dicts:
                events_summary["leave"][room_id] = {
                    "count": len(event_dicts),
                    "events": event_dicts
                }

    return events_summary


def display_events(events_summary):
    """
    Display a summary of processed events.

    Args:
        events_summary: Event summary dict from process_events()
    """
    if not any(events_summary.values()):
        print("No events found.")
        return

    print("Processed Events:")
    print(json.dumps(events_summary, indent=2, default=str))


async def send_message_to_room(client, room_identifier, message):
    """
    Send a message to a room identified by ID or alias.

    Args:
        client: The AsyncClient instance
        room_identifier: Room ID (!xyz:host) or alias (#alias:host)
        message: The message text to send

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Join room (handles both room IDs and aliases)
        join_resp = await client.join(room_identifier)

        if not isinstance(join_resp, JoinResponse):
            return False, f"Failed to join {room_identifier}: {str(join_resp)}"

        room_id = join_resp.room_id

        # Send message using the client's room_send method
        # matrix-nio handles encryption transparently for encrypted rooms
        resp = await client.room_send(
            room_id,
            "m.room.message",
            {
                "msgtype": "m.text",
                "body": message
            }
        )

        if isinstance(resp, RoomSendResponse):
            return True, f"Message sent to {room_identifier}"
        else:
            return False, f"Error sending message to {room_identifier}: {str(resp)}"

    except Exception as e:
        return False, f"Error: {str(e)}"


async def main():
    """Main entry point."""
    # Parse command line arguments using argparse
    parser = argparse.ArgumentParser(
        description="Synchronize Matrix events, accept invites, and send messages with E2E encryption.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python sync_and_invite.py alice
  python sync_and_invite.py alice '#myroom:localhost' 'Hello world!'
  python sync_and_invite.py alice '#myroom:localhost' 'Hello' --no-save-token
  python sync_and_invite.py alice --no-load-token  # sync from the beginning
  python sync_and_invite.py --no-save-token alice  # flag can be anywhere
        """
    )

    parser.add_argument(
        "username",
        help="Username as provided during registration (e.g., alice or @alice:localhost)"
    )
    parser.add_argument(
        "room_identifier",
        nargs="?",
        default=None,
        help="Optional room to send message to (e.g., #myroom:localhost or !xyz:localhost)"
    )
    parser.add_argument(
        "message",
        nargs="?",
        default=None,
        help="Optional message text to send (if omitted, only processes events)"
    )
    parser.add_argument(
        "--no-save-token",
        action="store_true",
        help="Prevent saving the sync token to account data (useful for testing)"
    )
    parser.add_argument(
        "--no-load-token",
        action="store_true",
        help="Skip loading the sync token, forcing a fresh sync from the beginning"
    )

    args = parser.parse_args()

    # Extract parsed arguments
    username = args.username
    room_identifier = args.room_identifier
    message = args.message
    no_save_token = args.no_save_token
    no_load_token = args.no_load_token

    # Validate input
    if not username or len(username) == 0:
        print("Error: Username cannot be empty")
        sys.exit(1)

    # Login
    success, result = await login_user(username)
    if not success:
        print(result)
        sys.exit(1)

    client, user_id, password = result
    server_url = "http://localhost:8008"

    print(f"Logged in as: {user_id}")
    print(f"Device ID: {client.device_id}\n")

    # Retrieve stored sync token from server account data
    print("Retrieving sync state...")
    if no_load_token:
        sync_token = None
        print("Skipping sync token load (--no-load-token flag set)")
    else:
        sync_token = await get_sync_token_from_server(client, user_id)
        if sync_token:
            print(f"Resuming from sync token: {sync_token[:20]}...")
        else:
            print("Starting fresh sync (no previous state)")

    # Perform sync
    print("Syncing events...")
    try:
        sync_resp = await client.sync(timeout=0, since=sync_token)
    except Exception as e:
        print(f"Sync failed: {str(e)}")
        await client.close()
        sys.exit(1)

    if not isinstance(sync_resp, SyncResponse):
        # Handle invalid/expired sync token by retrying without it
        if "Invalid stream token" in str(sync_resp) or "M_UNKNOWN" in str(sync_resp):
            print(f"Sync token expired, retrying with fresh sync...")
            try:
                sync_resp = await client.sync(timeout=0, since=None)
            except Exception as e:
                print(f"Fresh sync also failed: {str(e)}")
                await client.close()
                sys.exit(1)

            if not isinstance(sync_resp, SyncResponse):
                print(f"Sync failed: {str(sync_resp)}")
                await client.close()
                sys.exit(1)
        else:
            print(f"Sync failed: {str(sync_resp)}")
            await client.close()
            sys.exit(1)

    # Update sync token and store it (unless --no-save-token flag is set)
    new_sync_token = sync_resp.next_batch
    if new_sync_token:
        if no_save_token:
            print(f"Skipping sync token update (--no-save-token flag set)")
        else:
            print(f"Updating sync token...")
            await store_sync_token_to_server(client, user_id, new_sync_token)

    # Process and display events
    events_summary = process_events(sync_resp)
    display_events(events_summary)

    # Accept pending invites
    invited_rooms = sync_resp.rooms.invite
    if invited_rooms:
        print("\nAccepting pending invites...")
        await accept_pending_invites(client, invited_rooms)

    # Send message if specified
    if message:
        print(f"\nSending message to {room_identifier}...")
        success, msg = await send_message_to_room(client, room_identifier, message)
        print(msg)
        if not success:
            await client.close()
            sys.exit(1)

    await client.close()
    print("\nDone!")
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
