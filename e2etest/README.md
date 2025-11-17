# Matrix E2EE Test Programs

This directory contains 4 Python programs that demonstrate end-to-end encrypted messaging on a Matrix homeserver.

## Quick Start

1. **Initialize users and encryption keys:**
   ```bash
   python3 init.py
   ```
   This registers 2 random users and sets up their E2EE keys.
   Generates: `userconfig.json`

2. **Create an encrypted room and invite the second user:**
   ```bash
   python3 setup.py
   ```
   Creates a room with E2EE enabled and invites the second user.
   Generates: `roomconfig.json`

3. **Send an encrypted message (in one terminal):**
   ```bash
   python3 send.py
   ```

4. **Receive and decrypt messages (in another terminal):**
   ```bash
   python3 recv.py
   ```

## Program Details

### init.py
- **Purpose**: Register users and setup E2EE encryption
- **Actions**:
  - Generates random usernames (user_XXXXX format)
  - Registers both users on the Matrix homeserver
  - Creates Olm accounts for each user
  - Uploads device keys and one-time keys to the server
  - Saves user credentials and device IDs to `userconfig.json`
- **Config Output**: `userconfig.json` with user IDs, passwords, device IDs

### setup.py
- **Purpose**: Create an encrypted room and invite participants
- **Actions**:
  - Loads user credentials from `userconfig.json`
  - Logs in as the first user (sender/alice)
  - Creates a new room with encryption enabled (m.room.encryption)
  - Generates random room name (room_XXXXX format)
  - Invites the second user (receiver/bob) to the room
  - Saves room ID and name to `roomconfig.json`
- **Config Output**: `roomconfig.json` with room ID, name, encrypted flag

### send.py
- **Purpose**: Send an encrypted message to the test room
- **Actions**:
  - Loads user and room configs
  - Logs in as the first user with their device
  - Processes pending events
  - Joins the room (if needed)
  - Verifies the recipient's device (marks as trusted)
  - Sends an encrypted message
  - Waits 5 seconds to process server responses
- **Message Format**: "Hello from alice at ISO_TIMESTAMP!"

### recv.py
- **Purpose**: Receive and decrypt messages
- **Actions**:
  - Loads user and room configs
  - Logs in as the second user with their device
  - Processes pending events and accepts room invites
  - Sets up a message callback
  - Syncs with the server for up to 30 seconds, waiting for messages
  - Logs decrypted message content with sender and timestamp
  - Graceful shutdown on Ctrl+C
- **Output**: Message body, sender, and decryption status

## Configuration Files

### userconfig.json
```json
{
  "users": [
    {
      "username": "user_XXXXX",
      "password": "MD5_HASH",
      "user_id": "@user_XXXXX:localhost",
      "device_id": "DEVICE_ID",
      "registered_at": "ISO_TIMESTAMP"
    },
    ...
  ]
}
```

### roomconfig.json
```json
{
  "room_id": "!room_id:localhost",
  "room_name": "room_XXXXX",
  "created_at": "ISO_TIMESTAMP",
  "encrypted": true
}
```

## Technical Details

- **Matrix Server**: http://localhost:8008
- **Encryption Method**: Megolm (m.megolm.v1.aes-sha2)
- **Key Store**: `nio_store/` directory (persists encryption state)
- **Device Persistence**: Device IDs are preserved across runs to maintain trust
- **Device Verification**: All non-self devices are automatically marked as trusted for testing

## Logging

All programs output verbose logging to stdout with timestamps:
- `[DEBUG]`: Low-level database and sync operations
- `[INFO]`: High-level progress and status
- `[ERROR]`: Failures and exceptions
- `[WARNING]`: Non-critical issues

## Error Handling

- **Missing Configs**: Programs check for required config files and provide helpful error messages
- **Server Connection**: Timeout handling for sync operations
- **E2EE Failures**: Detailed error messages for encryption/decryption issues
- **Device Verification**: Clear logging of trust relationships

## Workflow

```
init.py (Register Users)
    ↓
    ↓ (generates userconfig.json)
    ↓
setup.py (Create Room)
    ↓
    ↓ (generates roomconfig.json)
    ↓
send.py (Send Message)    recv.py (Receive Message)
    ↓                              ↓
    └──────────────────────────────┘
         (encrypted message)
```

## Notes

- Each run of `init.py` creates new users with random usernames
- Multiple test runs can be done without clearing previous configs
- The `nio_store/` directory must not be deleted between send/recv runs
- Messages are fully encrypted end-to-end; the server cannot read them
- Device verification is automatic for testing; in production, you'd want explicit verification

