#!/usr/bin/env python3
"""
Synchronize Matrix events, accept pending invites, and send messages.

This program logs in a user, processes incoming events from the Matrix sync protocol,
automatically accepts pending invites, and optionally sends a message to a specified room.

The sync cursor is persisted server-side using the Matrix account data API, allowing
the client to resume from where it left off on subsequent runs without reprocessing events.

Examples:
  python sync_and_invite.py alice '#myroom:localhost'
  python sync_and_invite.py alice '#myroom:localhost' 'Hello from sync_and_invite!'
  python sync_and_invite.py alice '!roomid:localhost'
"""

import sys
import hashlib
import requests
import json
import argparse
from urllib.parse import urljoin
from matrix_client.client import MatrixClient
from matrix_client.errors import MatrixRequestError


def get_server_url():
    """Return the Matrix server URL."""
    return "http://localhost:8008"


def check_server_connectivity(server_url):
    """Check if the server is reachable."""
    try:
        response = requests.get(f"{server_url}/_matrix/client/versions", timeout=5)
        return response.status_code == 200
    except (requests.ConnectionError, requests.Timeout):
        return False


def login_user(username):
    """
    Login to the Matrix homeserver and return a MatrixClient.

    Args:
        username: The username (e.g., alice) or full user ID format (@alice:localhost)

    Returns:
        Tuple of (success: bool, (client: MatrixClient, user_id: str) or message: str)
    """
    server_url = get_server_url()

    # Check server connectivity
    if not check_server_connectivity(server_url):
        return False, f"Error: Cannot connect to Matrix server at {server_url}"

    # Extract the plain username for password derivation
    if username.startswith("@") and ":" in username:
        plain_username = username[1:username.index(":")]
        user_id_to_try = username
    else:
        plain_username = username
        user_id_to_try = f"@{username}:localhost"

    # Derive password from the plain username as MD5 hash
    password = hashlib.md5(plain_username.encode()).hexdigest()

    # Create Matrix client
    client = MatrixClient(server_url)

    try:
        # MatrixClient.login returns the access token as a string
        access_token = client.login(user_id_to_try, password)
        # User ID is stored in the client after login
        user_id = client.user_id
        return True, (client, user_id)
    except MatrixRequestError as e:
        return False, f"Login failed: {str(e)}"
    except Exception as e:
        return False, f"Error during login: {str(e)}"


def get_sync_token_from_server(server_url, user_id, access_token):
    """
    Retrieve the stored sync token from the server's account data.

    Args:
        server_url: The Matrix homeserver URL
        user_id: The user ID (@user:host format)
        access_token: The user's access token

    Returns:
        The sync token string, or None if not found
    """
    url = urljoin(server_url, f"/_matrix/client/r0/user/{user_id}/account_data/org.matrix.sync_token")

    try:
        response = requests.get(
            url,
            params={"access_token": access_token},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("sync_token")
        elif response.status_code == 404:
            # No stored sync token yet
            return None
        else:
            return None
    except Exception:
        return None


def store_sync_token(client, user_id, sync_token):
    """
    Store the sync token in the server's account data.

    Args:
        client: The MatrixClient instance
        user_id: The user ID (@user:host format)
        sync_token: The sync token to store

    Returns:
        True if successful, False otherwise
    """
    try:
        client.api.set_account_data(
            user_id,
            "org.matrix.sync_token",
            {"sync_token": sync_token}
        )
        return True
    except Exception as e:
        print(f"Warning: Failed to store sync token: {str(e)}")
        return False


def accept_pending_invites(client, invited_rooms):
    """
    Accept all pending room invitations.

    Args:
        client: The MatrixClient instance
        invited_rooms: Dict of room_id -> room_data from sync response

    Returns:
        List of room IDs that were joined
    """
    joined = []

    for room_id in invited_rooms.keys():
        try:
            client.join_room(room_id)
            print(f"Accepted invite: {room_id}")
            joined.append(room_id)
        except MatrixRequestError as e:
            print(f"Error accepting invite for {room_id}: {str(e)}")

    return joined


def process_events(sync_data):
    """
    Extract and format events from sync response.

    Args:
        sync_data: The sync response data

    Returns:
        Dict with event summaries
    """
    rooms = sync_data.get("rooms", {})

    events_summary = {
        "join": {},
        "invite": {},
        "leave": {}
    }

    # Process joined rooms
    for room_id, room_data in rooms.get("join", {}).items():
        events = room_data.get("timeline", {}).get("events", [])
        if events:
            events_summary["join"][room_id] = {
                "count": len(events),
                "events": events
            }

    # Process invited rooms
    for room_id, room_data in rooms.get("invite", {}).items():
        invite_state = room_data.get("invite_state", {}).get("events", [])
        if invite_state:
            events_summary["invite"][room_id] = {
                "count": len(invite_state),
                "events": invite_state
            }

    # Process left rooms
    for room_id, room_data in rooms.get("leave", {}).items():
        events = room_data.get("timeline", {}).get("events", [])
        if events:
            events_summary["leave"][room_id] = {
                "count": len(events),
                "events": events
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


def send_message_to_room(client, room_identifier, message):
    """
    Send a message to a room identified by ID or alias.

    Args:
        client: The MatrixClient instance
        room_identifier: Room ID (!xyz:host) or alias (#alias:host)
        message: The message text to send

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # join_room handles both room IDs and aliases
        room = client.join_room(room_identifier)

        # Send the message
        room.send_text(message)

        return True, f"Message sent to {room_identifier}"
    except MatrixRequestError as e:
        return False, f"Error sending message to {room_identifier}: {str(e)}"
    except Exception as e:
        return False, f"Error: {str(e)}"


def main():
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

    args = parser.parse_args()

    # Extract parsed arguments
    username = args.username
    room_identifier = args.room_identifier
    message = args.message
    no_save_token = args.no_save_token

    # Validate input
    if not username or len(username) == 0:
        print("Error: Username cannot be empty")
        sys.exit(1)

    # Login
    success, result = login_user(username)
    if not success:
        print(result)
        sys.exit(1)

    client, user_id = result
    server_url = get_server_url()

    print(f"Logged in as: {user_id}")
    print(f"Device ID: {client.device_id}\n")

    # Retrieve stored sync token
    print("Retrieving sync state...")
    sync_token = get_sync_token_from_server(server_url, user_id, client.token)
    if sync_token:
        print(f"Resuming from sync token: {sync_token[:20]}...")
    else:
        print("Starting fresh sync (no previous state)")

    # Perform sync
    print("Syncing events...")
    try:
        sync_data = client.api.sync(since=sync_token, timeout_ms=0)
    except MatrixRequestError as e:
        print(f"Sync failed: {str(e)}")
        sys.exit(1)

    # Update sync token and store it
    new_sync_token = sync_data.get("next_batch")
    if new_sync_token:
        print(f"Updating sync token...")
        store_sync_token(client, user_id, new_sync_token)
        client.sync_token = new_sync_token

    # Process and display events
    events_summary = process_events(sync_data)
    display_events(events_summary)

    # Accept pending invites
    invited_rooms = sync_data.get("rooms", {}).get("invite", {})
    if invited_rooms:
        print("\nAccepting pending invites...")
        accept_pending_invites(client, invited_rooms)

    # Send message if specified
    if message:
        print(f"\nSending message to {room_identifier}...")
        success, msg = send_message_to_room(client, room_identifier, message)
        print(msg)
        if not success:
            sys.exit(1)

    print("\nDone!")
    sys.exit(0)


if __name__ == "__main__":
    main()
