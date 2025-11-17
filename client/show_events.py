#!/usr/bin/env python3
"""
Show pending events for a Matrix user.

This program takes a username (e.g., alice) or full user ID format (@alice:localhost)
and displays pending events in formatted JSON.

The password is derived as MD5(username) to match the registration process.

Examples:
  python show_events.py alice
  python show_events.py @alice:localhost
"""

import sys
import hashlib
import requests
import json
from urllib.parse import urljoin


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
    Login to the Matrix homeserver.

    Args:
        username: The username (e.g., alice) or full user ID format (@alice:localhost)

    Returns:
        Tuple of (success: bool, (access_token, user_id, device_id) or message: str)
    """
    server_url = get_server_url()

    # Check server connectivity
    if not check_server_connectivity(server_url):
        return False, f"Error: Cannot connect to Matrix server at {server_url}"

    # Extract the plain username for password derivation
    if username.startswith("@") and ":" in username:
        # Extract localpart from full user ID format (@alice:localhost -> alice)
        plain_username = username[1:username.index(":")]
        user_id_to_try = username
    else:
        # Plain username
        plain_username = username
        user_id_to_try = f"@{username}:localhost"

    # Derive password from the plain username as MD5 hash
    password = hashlib.md5(plain_username.encode()).hexdigest()

    # Login endpoint
    login_url = urljoin(server_url, "/_matrix/client/r0/login")

    try:
        data = {
            "type": "m.login.password",
            "user": user_id_to_try,
            "password": password
        }

        response = requests.post(login_url, json=data, timeout=10)

        if response.status_code == 200:
            result = response.json()
            access_token = result.get("access_token")
            user_id = result.get("user_id")
            device_id = result.get("device_id")
            return True, (access_token, user_id, device_id)

        elif response.status_code == 429:
            return False, "Login failed: Rate limited by server"
        else:
            return False, "Login failed: Invalid username or password"

    except requests.RequestException as e:
        return False, f"Error during login: {str(e)}"


def get_pending_events(access_token):
    """
    Fetch pending events from the server.

    Args:
        access_token: The user's access token

    Returns:
        Tuple of (success: bool, events: dict or message: str)
    """
    server_url = get_server_url()

    # Sync endpoint
    sync_url = urljoin(server_url, "/_matrix/client/r0/sync")

    try:
        params = {
            "access_token": access_token,
            "timeout": 0  # Non-blocking sync
        }

        response = requests.get(sync_url, params=params, timeout=10)

        if response.status_code == 200:
            result = response.json()
            return True, result

        elif response.status_code == 401:
            return False, "Sync failed: Unauthorized (invalid access token)"

        elif response.status_code == 429:
            return False, "Sync failed: Rate limited by server"

        else:
            error_data = response.json()
            error_msg = error_data.get("error", "Unknown error")
            return False, f"Sync failed: {error_msg}"

    except requests.RequestException as e:
        return False, f"Error during sync: {str(e)}"


def format_events(sync_data):
    """
    Extract and format events from sync response.

    Args:
        sync_data: The sync response data

    Returns:
        Formatted event data
    """
    rooms = sync_data.get("rooms", {})

    events_data = {
        "join": {},
        "invite": {},
        "leave": {}
    }

    # Process joined rooms
    for room_id, room_data in rooms.get("join", {}).items():
        events = room_data.get("timeline", {}).get("events", [])
        if events:
            events_data["join"][room_id] = events

    # Process invited rooms
    for room_id, room_data in rooms.get("invite", {}).items():
        invite_state = room_data.get("invite_state", {}).get("events", [])
        if invite_state:
            events_data["invite"][room_id] = invite_state

    # Process left rooms
    for room_id, room_data in rooms.get("leave", {}).items():
        events = room_data.get("timeline", {}).get("events", [])
        if events:
            events_data["leave"][room_id] = events

    return events_data


def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: python show_events.py <username>")
        print("")
        print("Where:")
        print("  <username>: Username as provided during registration (e.g., alice or @alice:localhost)")
        print("")
        print("Examples:")
        print("  python show_events.py alice")
        print("  python show_events.py @alice:localhost")
        sys.exit(1)

    username = sys.argv[1]

    # Validate input
    if not username or len(username) == 0:
        print("Error: Username cannot be empty")
        sys.exit(1)

    # Login
    success, result = login_user(username)
    if not success:
        print(result)
        sys.exit(1)

    access_token, user_id, device_id = result
    print(f"Logged in as: {user_id}")
    print(f"Device ID: {device_id}\n")

    # Get pending events
    success, result = get_pending_events(access_token)
    if not success:
        print(result)
        sys.exit(1)

    # Format and display events
    events = format_events(result)

    if any(events["join"].values()) or any(events["invite"].values()) or any(events["leave"].values()):
        print("Pending Events:")
        print(json.dumps(events, indent=2))
    else:
        print("No pending events found.")

    sys.exit(0)


if __name__ == "__main__":
    main()
