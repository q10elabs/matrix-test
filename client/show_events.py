#!/usr/bin/env python3
"""
Show pending events for a Matrix user using matrix-nio.

This program takes a username (e.g., alice) or full user ID format (@alice:localhost)
and displays pending events in formatted JSON.

The password is derived as MD5(username) to match the registration process.

Uses the modern matrix-nio async client library.

Examples:
  python show_events.py alice
  python show_events.py @alice:localhost
"""

import sys
import hashlib
import json
import asyncio
from nio import AsyncClient
from nio.responses import LoginResponse, SyncResponse


async def login_user(username):
    """
    Login to the Matrix homeserver.

    Args:
        username: The username (e.g., alice) or full user ID format (@alice:localhost)

    Returns:
        Tuple of (success: bool, (client: AsyncClient, user_id: str) or message: str)
    """
    server_url = "http://localhost:8008"

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

    # Create async client
    client = AsyncClient(server_url, user_id_to_try)

    try:
        # Login
        resp = await client.login(password)

        if isinstance(resp, LoginResponse):
            user_id = resp.user_id
            device_id = resp.device_id
            return True, (client, user_id, device_id)
        else:
            # Handle error response
            error_msg = str(resp)
            await client.close()
            return False, f"Login failed: {error_msg}"

    except Exception as e:
        await client.close()
        return False, f"Error during login: {str(e)}"


async def get_pending_events(client):
    """
    Fetch pending events from the server using sync.

    Args:
        client: The AsyncClient instance

    Returns:
        Tuple of (success: bool, events: dict or message: str)
    """
    try:
        # Perform sync with no timeout (non-blocking)
        resp = await client.sync(timeout=0)

        if isinstance(resp, SyncResponse):
            return True, resp
        else:
            # Handle error response
            error_msg = str(resp)
            return False, f"Sync failed: {error_msg}"

    except Exception as e:
        return False, f"Error during sync: {str(e)}"


def format_events(sync_resp):
    """
    Extract and format events from sync response.

    Args:
        sync_resp: The SyncResponse object

    Returns:
        Formatted event data
    """
    events_data = {
        "join": {},
        "invite": {},
        "leave": {}
    }

    # Process joined rooms
    for room_id, room_data in sync_resp.rooms.join.items():
        events = room_data.timeline.events
        if events:
            # Convert event objects to dictionaries for JSON serialization
            event_dicts = []
            for event in events:
                # Build event dict from available attributes
                event_dict = {}

                # Get event type - different event classes have different attributes
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

                # Store string representation if no attributes found
                if not event_dict:
                    event_dict["raw"] = str(event)

                event_dicts.append(event_dict)

            events_data["join"][room_id] = event_dicts

    # Process invited rooms
    for room_id, room_data in sync_resp.rooms.invite.items():
        # Invited rooms have invite_state with limited events
        if room_data.invite_state:
            event_dicts = []
            for event in room_data.invite_state:
                if isinstance(event, dict):
                    event_dicts.append(event)
                else:
                    # Try to extract attributes
                    event_dict = {}
                    for attr in ['type', 'sender', 'event_id', 'content']:
                        if hasattr(event, attr):
                            event_dict[attr] = getattr(event, attr)
                    if event_dict:
                        event_dicts.append(event_dict)

            if event_dicts:
                events_data["invite"][room_id] = event_dicts

    # Process left rooms
    for room_id, room_data in sync_resp.rooms.leave.items():
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

                if event_dict:
                    event_dicts.append(event_dict)

            if event_dicts:
                events_data["leave"][room_id] = event_dicts

    return events_data


async def main():
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
    success, result = await login_user(username)
    if not success:
        print(result)
        sys.exit(1)

    client, user_id, device_id = result
    print(f"Logged in as: {user_id}")
    print(f"Device ID: {device_id}\n")

    # Get pending events
    success, result = await get_pending_events(client)
    if not success:
        print(result)
        await client.close()
        sys.exit(1)

    # Format and display events
    events = format_events(result)

    if any(events["join"].values()) or any(events["invite"].values()) or any(events["leave"].values()):
        print("Pending Events:")
        print(json.dumps(events, indent=2, default=str))
    else:
        print("No pending events found.")

    await client.close()
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
