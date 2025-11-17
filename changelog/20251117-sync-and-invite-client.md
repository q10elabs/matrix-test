# Sync and Invite Client Program

## Task Specification

Create a new client program (`sync_and_invite.py`) that:
1. Synchronizes and displays events using Matrix's native sync protocol
2. Accepts pending invites (processes invite events)
3. Advances the sync cursor to avoid reprocessing the same events
4. Takes a room name and optional message on the command line
5. Sends the optional message to the specified room after processing events

## High-Level Decisions

1. **Sync token persistence**: Use Matrix's native account data API to store sync tokens server-side. This allows the client to resume syncing from the last position across sessions without local file storage.
   - Store sync token using `api.set_account_data()` with type `"org.matrix.sync_token"`
   - Retrieve on startup via direct GET request to `/_matrix/client/r0/user/{user_id}/account_data/org.matrix.sync_token`
   - Note: matrix_client library doesn't provide a getter, but requests library can be used directly

2. **Invite acceptance**: Auto-accept all pending invites by calling `api.join_room()` for each room_id in the invite section of sync response

3. **Room identifier**: Support both room IDs (e.g., `!xyz:localhost`) and room aliases (e.g., `#myroom:localhost`). The `join_room()` method accepts both formats.

4. **Event processing and message sending**:
   - Process all incoming events from sync (timeline events in joined rooms, invite events)
   - After accepting invites, send optional message to specified room
   - Use `room.send_text()` to send message (room object obtained from client.rooms dict or after joining)

## Requirements Changes

None yet

## Files Modified

- **Created**: `client/sync_and_invite.py` - Main sync and invite client program (278 lines)

## Rationales and Alternatives

1. **Account data for sync token**: Matrix protocol stores account data server-side via PUT `/user/{userId}/account_data/{type}`. This is the native way to persist client state without local file I/O.

2. **Auto-accept invites**: Simplified approach - users can invite and have bot immediately accept. Alternative would be selective accept, but requirements specified auto-accept.

3. **Room identifier support**: Both aliases and IDs use same API endpoint (`join_room()` handles resolution), providing maximum flexibility.

4. **Event display format**: JSON output for consistency with `show_events.py`, maintaining clear event structure for debugging/logging.

## Obstacles and Solutions

1. **MatrixClient.login return format**: Expected tuple, actually returns string (access token). Solution: Extract `user_id` from `client.user_id` property after login.

2. **sync_forever not available**: Attempted to use non-existent method. Solution: Use `client.api.sync()` directly with `since` parameter for single sync operation.

3. **Shell escaping of room IDs**: `!` character in room IDs gets escaped by bash. Solution: Documented that room aliases work better from command line, IDs need proper quoting.

## Current Status

**COMPLETED** - All functionality implemented and tested:
- ✅ Login and token management
- ✅ Sync token persistence via account data API
- ✅ Event processing and display (JSON format)
- ✅ Automatic invite acceptance
- ✅ Message sending to rooms (both aliases and IDs)
- ✅ Sync cursor advancement prevents re-processing

**Test Results**:
- Alice sends message to room → verified
- Bob receives invite, accepts it, sends message → verified
- Sync cursor properly stored and resumed → verified
- No events reprocessed after cursor advancement → verified
