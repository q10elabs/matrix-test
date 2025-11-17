# E2EE Test Programs Implementation

## Task Specification
Create 4 programs to demonstrate E2E encrypted messaging on a local Matrix server:
- **init**: Register two users and set up E2EE keys (upload to server)
- **setup**: Create encrypted room and invite second user
- **send**: Send encrypted message to room
- **recv**: Receive and decrypt messages from room

Configuration sharing with auto-generated usernames and room names:
- `userconfig.json`: Stores auto-generated usernames, passwords, user IDs, device IDs
- `roomconfig.json`: Stores auto-generated room name, room ID, encryption flag

## High-Level Decisions

1. **Configuration Format**: JSON for simplicity (easy to parse/serialize)
2. **Username/Room Generation**: Random format (user_XXXXX, room_XXXXX) persisted to configs
3. **User Mapping**: First user in config = sender (alice), second user = receiver (bob)
4. **Device Management**: Preserve device IDs across runs using `store_path` (nio_store/)
5. **Device Verification**: Auto-verify all non-self devices in E2EE flow (testing simplification)
6. **Key Upload**: Uses matrix-nio's `client.keys_upload()` after `client.olm.share_keys()`

## Files Modified

Created:
- `e2etest/init.py`: User registration + E2EE key setup
- `e2etest/setup.py`: Encrypted room creation + user invitation
- `e2etest/send.py`: Send encrypted message (with device verification)
- `e2etest/recv.py`: Receive + decrypt messages with callbacks

## Rationales and Alternatives

- **Random Names**: Allows multiple test runs without name conflicts
- **First/Second User Mapping**: Simpler than hardcoding "alice"/"bob" names
- **Auto Device Verification**: Required for E2E to work; in testing we trust all devices
- **JSON Config Format**: More human-readable than pickle, works cross-platform

## Obstacles and Solutions

1. **ModuleNotFoundError (nio)**: Used venv's Python interpreter
2. **keys_upload() API**: Takes no args (uses internal share_keys data)
3. **Device Not Verified**: Added `client.olm.verify_device()` for test devices
4. **Room Send Failed**: Added `client.sync()` after `join()` to load room state
5. **User Hardcoding**: Changed from "alice"/"bob" to indexed user config access

## Current Status
- ✓ init.py: Registers 2 users, generates credentials, uploads E2EE keys
- ✓ setup.py: Creates encrypted room, invites second user, saves room config
- ✓ send.py: Sends encrypted message successfully
- ✓ recv.py: Implemented (callback-based message receiver)
- ✓ All config/database files now contained in e2etest/ directory
- **Final**: All programs tested and working with localized file storage
