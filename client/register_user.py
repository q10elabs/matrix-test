#!/usr/bin/env python3
"""
Register a user to a Matrix homeserver.

This program takes a username as an argument and registers it with the server
at localhost:8008. The password is the MD5 hash of the username.
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


def set_display_name(user_id, display_name, access_token=None):
    """
    Set the display name for a user.

    Args:
        user_id: The full user ID (e.g., @5:localhost)
        display_name: The display name to set
        access_token: Optional access token for authentication

    Returns:
        None (prints status to stdout)
    """
    server_url = get_server_url()
    set_displayname_url = urljoin(server_url, f"/_matrix/client/r0/profile/{user_id}/displayname")

    data = {"displayname": display_name}
    params = {}
    if access_token:
        params["access_token"] = access_token

    try:
        response = requests.put(set_displayname_url, json=data, params=params, timeout=10)

        if response.status_code == 200:
            print(f"Display name set to: {display_name}")
        else:
            print(f"Warning: Failed to set display name (status {response.status_code}): {response.text}")

    except requests.RequestException as e:
        print(f"Warning: Error setting display name: {str(e)}")


def register_user(username):
    """
    Register a user on the Matrix homeserver.

    Args:
        username: The username to register

    Returns:
        Tuple of (success: bool, message: str, access_token: str or None)
    """
    server_url = get_server_url()

    # Check server connectivity
    if not check_server_connectivity(server_url):
        return False, f"Error: Cannot connect to Matrix server at {server_url}", None

    # Calculate password as MD5 hash of username
    password = hashlib.md5(username.encode()).hexdigest()

    # Registration endpoint
    register_url = urljoin(server_url, "/_matrix/client/r0/register")

    # Prepare registration data
    # Note: Use 'username' parameter, not 'user' - 'user' is ignored
    data = {
        "kind": "user",
        "auth": {"type": "m.login.dummy"},
        "username": username,
        "password": password,
        "initial_device_display_name": "Test Device"
    }

    try:
        # Register with auth
        response = requests.post(register_url, json=data, timeout=10)

        # Handle different response codes
        if response.status_code == 200:
            result = response.json()
            user_id = result.get("user_id", "unknown")
            device_id = result.get("device_id", "unknown")
            access_token = result.get("access_token", "")

            # Store credentials for later use
            success_msg = f"User registered successfully!\nUser ID: {user_id}\nDevice ID: {device_id}"
            if access_token:
                success_msg += f"\nAccess Token: {access_token}"
            return True, success_msg, access_token

        elif response.status_code == 400:
            error_data = response.json()
            error_msg = error_data.get("error", "Unknown error")
            return False, f"Registration failed: {error_msg}", None

        elif response.status_code == 429:
            return False, "Registration failed: Rate limited by server", None

        else:
            return False, f"Registration failed with status {response.status_code}: {response.text}", None

    except requests.RequestException as e:
        return False, f"Error during registration: {str(e)}", None


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python register_user.py <username> [display_name]")
        print("")
        print("Arguments:")
        print("  <username>:     Username for login (MD5 hash used as password)")
        print("  [display_name]: Optional display name for the user profile")
        print("")
        print("Examples:")
        print("  python register_user.py alice")
        print("  python register_user.py alice 'Alice Smith'")
        sys.exit(1)

    username = sys.argv[1]
    display_name = sys.argv[2] if len(sys.argv) > 2 else None

    # Validate username format
    if not username or len(username) == 0:
        print("Error: Username cannot be empty")
        sys.exit(1)

    success, message, access_token = register_user(username)
    print(message)

    if success and display_name:
        # Extract user_id from message
        import re
        match = re.search(r'User ID: (@[^:]+:localhost)', message)
        if match:
            user_id = match.group(1)
            # Set display name
            set_display_name(user_id, display_name, access_token)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
