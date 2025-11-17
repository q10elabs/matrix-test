# E2EE Test Suite - Node.js Implementation

A Node.js implementation of end-to-end encryption (E2EE) tests using `matrix-js-sdk`, mirroring the Python test suite in the `e2etest/` directory.

## Overview

This test suite demonstrates:
- User registration and device creation
- End-to-end encryption setup (Olm key generation and upload)
- Encrypted room creation
- Encrypted message sending and receiving

## Prerequisites

- Node.js 18+ with npm or yarn
- Matrix homeserver running at `http://localhost:8008`
- `matrix-js-sdk` available (installed via yarn)

## Setup

### Install Dependencies

```bash
cd e2eetest-js
yarn install
```

This installs:
- `matrix-js-sdk` - The main Matrix client SDK
- `tsx` - TypeScript execution without build step
- TypeScript and Node types

## Usage

Run the test programs in sequence. Each program is independently executable.

### 1. Initialize Users and Encryption Keys

```bash
yarn init
```

This program:
- Registers two random users with the Matrix homeserver
- Sets up Olm encryption for each user
- Uploads device keys and one-time keys to the server
- Saves user credentials to `userconfig.json`

**Output:**
- `userconfig.json` - User credentials and device IDs

### 2. Setup Encrypted Room

```bash
yarn setup
```

This program:
- Logs in as the first user (alice)
- Creates a new room with encryption enabled (`m.megolm.v1.aes-sha2`)
- Invites the second user (bob) to the room
- Saves room details to `roomconfig.json`

**Output:**
- `roomconfig.json` - Room ID and metadata

### 3. Send Encrypted Message

In one terminal:

```bash
yarn send
```

This program:
- Logs in as the first user (alice)
- Processes pending events
- Joins the encrypted room
- Sends an encrypted message
- Waits 5 seconds for further events

### 4. Receive and Decrypt Messages

In another terminal (while `send` is running):

```bash
yarn recv
```

This program:
- Logs in as the second user (bob)
- Accepts room invitations
- Syncs continuously for 30 seconds
- Logs all received messages with decryption status
- Handles Ctrl+C gracefully

## Architecture

### Directory Structure

```
e2eetest-js/
├── src/
│   ├── utils/
│   │   ├── logger.ts      # Formatted logging with timestamps
│   │   ├── config.ts      # Load/save JSON configuration files
│   │   └── client.ts      # Client creation and E2EE setup
│   ├── init.ts            # User registration and key setup
│   ├── setup.ts           # Room creation and invitations
│   ├── send.ts            # Send encrypted messages
│   └── recv.ts            # Receive and decrypt messages
├── store/                 # Crypto state storage (created at runtime)
├── package.json
├── tsconfig.json
└── README.md
```

### Key Modules

#### `logger.ts`
Provides formatted console output with timestamps and log levels (DEBUG, INFO, WARN, ERROR).

#### `config.ts`
Manages JSON configuration files:
- `userconfig.json` - User credentials, passwords, user IDs, device IDs
- `roomconfig.json` - Room ID, name, and metadata

#### `client.ts`
Client management utilities:
- Create Matrix client with E2EE support
- Login and sync
- Upload encryption keys
- Close client

## Configuration Files

### userconfig.json

```json
{
  "users": [
    {
      "username": "user_12345",
      "password": "user_12345",
      "user_id": "@user_12345:localhost",
      "device_id": "ABCDEFGHIJ",
      "registered_at": "2025-01-17T10:30:00.000Z"
    }
  ]
}
```

### roomconfig.json

```json
{
  "room_id": "!abcdef123456:localhost",
  "room_name": "room_12345",
  "created_at": "2025-01-17T10:31:00.000Z",
  "creator": "@user_12345:localhost"
}
```

## Features

- **TypeScript Support** - Direct execution with `tsx`, no build step required
- **Async/Await** - Modern async patterns throughout
- **Structured Logging** - Timestamped, level-based logging
- **E2EE Support** - Full Olm encryption setup and message encryption
- **Graceful Shutdown** - Handles Ctrl+C for clean exit
- **Device Trust** - Marks devices as trusted for E2E testing
- **Auto-join Rooms** - Automatically accepts invitations

## Development

### Type Checking

TypeScript types are checked at runtime via `tsx`. For explicit type checking:

```bash
# (Not included by default, but can be added if needed)
npx tsc --noEmit
```

### Debugging

All programs support verbose logging:

```bash
DEBUG=* yarn init  # Enable all debug output
```

Or check the logger output in the source code.

## Troubleshooting

### Module Resolution Issues

Ensure you're using the correct import syntax for ES modules:

```typescript
import { createClient } from "matrix-js-sdk";
import { logger } from "./utils/logger.js";  // Note the .js extension
```

### Crypto Initialization Errors

If you see crypto errors:
1. Ensure the store directory exists (created automatically)
2. Check that the Matrix homeserver is running at `http://localhost:8008`
3. Verify user registration succeeded before running setup

### Connection Issues

If programs can't connect to the server:
1. Verify the server is running: `curl http://localhost:8008`
2. Check the `SERVER_URL` constant in source files
3. Ensure firewall allows connections to port 8008

## Comparison with Python Implementation

This Node.js version mirrors the Python test suite in `e2etest/`:

| Feature | Python | Node.js |
|---------|--------|---------|
| Client Library | matrix-nio | matrix-js-sdk |
| Language | Python 3 | TypeScript |
| Execution | Direct Python | tsx (no build) |
| Encryption | Olm (via matrix-nio) | Olm (via matrix-js-sdk) |
| Config Format | JSON | JSON (identical) |
| Program Flow | Same | Same |

## License

ISC
