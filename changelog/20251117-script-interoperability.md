# Script Interoperability Fix

## Task Specification
Fix the `register_user.py` and `show_events.py` scripts so they work together. The issue: users registered with `register_user.py` cannot be reused by `show_events.py`, particularly with random usernames.

## Investigation Summary
Found the root cause through testing and server logs:

**The Problem:**
- When registering with `register_user.py randomuser456`, the Matrix server ignores the requested username
- The server generates a hash-based user ID instead (e.g., @1da60a1eb22a2ace25efedaf0fdea4d2:localhost)
- Registration succeeds and reports the hash-based user ID
- When `show_events.py randomuser456` tries to login, it attempts "@randomuser456:localhost" which doesn't exist
- Server logs confirm: "Attempted to login as @randomuser456:localhost but they do not exist"

**Root Cause:**
In `register_user.py` line 43: `await client.register(password, username, device_name="Test Device")`
The `username` parameter is being passed but the Matrix client library may not be using it correctly, or the server is configured to ignore it.

## Implementation Plan
**Option 1 (Recommended):** Fix the registration call in register_user.py to not pass a username parameter and let the server assign it, then extract and save/display the actual registered user ID properly.

**Option 2:** Use the user ID returned from registration and update show_events.py to accept user IDs.

**Option 3:** Configure the Matrix server to honor the username during registration (requires server config changes).

Recommend Option 1 as it fixes the client-side logic without requiring server changes.

## Solution Implemented
**The Fix:** Corrected the parameter order in `register_user.py` line 43.

The matrix-nio `AsyncClient.register()` method signature is:
```python
async def register(self, username: str, password: str, device_name: str = "", ...)
```

The original code had parameters in the wrong order:
```python
# WRONG:
resp = await client.register(password, username, device_name="Test Device")

# CORRECT:
resp = await client.register(username, password, device_name="Test Device")
```

## Files Modified
- `client/register_user.py`: Fixed parameter order in register() call (line 43)

## Testing Results
✅ Fixed usernames work: `register_user.py testuser_fixed` → `show_events.py testuser_fixed`
✅ Random usernames work: `register_user.py randomuser_1763384969` → `show_events.py randomuser_1763384969`

## Current Status
Complete - both scripts now work together correctly.
