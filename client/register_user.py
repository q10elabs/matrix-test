#!/usr/bin/env python3
"""
Register a user to a Matrix homeserver using matrix-nio.

This program takes a username as an argument and registers it with the server
at localhost:8008. The password is the MD5 hash of the username.

Uses the modern matrix-nio async client library instead of raw HTTP requests.

Examples:
  python register_user.py alice
  python register_user.py alice 'Alice Smith'
"""

import sys
import hashlib
import asyncio
from nio import AsyncClient
from nio.responses import RegisterResponse


async def register_user(username, display_name=None):
    """
    Register a user on the Matrix homeserver.

    Args:
        username: The username to register
        display_name: Optional display name for the user profile

    Returns:
        Tuple of (success: bool, message: str, user_id: str or None)
    """
    server_url = "http://localhost:8008"

    # Calculate password as MD5 hash of username
    password = hashlib.md5(username.encode()).hexdigest()

    # Create async client
    client = AsyncClient(server_url, username)

    try:
        # Register user
        resp = await client.register(password, username, device_name="Test Device")

        if isinstance(resp, RegisterResponse):
            user_id = resp.user_id
            device_id = resp.device_id

            success_msg = f"User registered successfully!\nUser ID: {user_id}\nDevice ID: {device_id}"

            # Set display name if provided
            if display_name:
                # Set display name after registration
                try:
                    dn_resp = await client.set_displayname(display_name)
                    # Check if response indicates success
                    if hasattr(dn_resp, 'status_code') and dn_resp.status_code == 200:
                        success_msg += f"\nDisplay name set to: {display_name}"
                    elif not hasattr(dn_resp, 'status_code'):
                        success_msg += f"\nDisplay name set to: {display_name}"
                    else:
                        success_msg += f"\nWarning: Could not set display name"
                except Exception as dn_err:
                    success_msg += f"\nWarning: Could not set display name: {str(dn_err)}"

            await client.close()
            return True, success_msg, user_id

        else:
            # Handle error response
            error_msg = str(resp)
            await client.close()
            return False, f"Registration failed: {error_msg}", None

    except Exception as e:
        await client.close()
        return False, f"Error during registration: {str(e)}", None


async def main():
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

    success, message, user_id = await register_user(username, display_name)
    print(message)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
