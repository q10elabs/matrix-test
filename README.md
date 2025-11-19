# Matrix Protocol Learning Project

A hands-on learning project to explore the Matrix protocol through experimentation. This repository demonstrates how to set up a local Matrix homeserver, build client applications, and test end-to-end encryption capabilities.

## Project Overview

**Goal**: Learn the basics of the Matrix protocol through practical experiments, from server setup to encrypted messaging.

**What's Included**:
- Local Matrix homeserver configuration (Synapse)
- Client utilities for user registration and basic operations
- End-to-end encryption test programs using the matrix-nio library
- Multiple test scenarios demonstrating different aspects of the protocol

## Repository Structure

```
.
├── server/                 # Synapse homeserver configuration
│   ├── homeserver.yaml     # Main server configuration
│   ├── homeserver.db       # SQLite database (persists state)
│   ├── log.yaml            # Logging configuration
│   └── requirements.txt     # Server dependencies
│
├── client/                 # Core client utilities
│   ├── register_user.py    # User registration utility
│   ├── sync_and_invite.py  # Sync and room invitation logic
│   ├── show_events.py      # Event display utility
│   ├── encryption.py       # Encryption helper functions
│   └── test_e2e.py         # Unit tests for E2EE
│
├── e2etest/                # End-to-end encryption test (Python)
│   ├── README.md           # Detailed E2EE test documentation
│   ├── init.py             # Register users and setup E2EE keys
│   ├── setup.py            # Create encrypted room and invite users
│   ├── send.py             # Send encrypted message
│   ├── recv.py             # Receive and decrypt message
│   ├── userconfig.json     # Generated user credentials
│   └── roomconfig.json     # Generated room configuration
│
├── e2eetest-js/            # E2EE tests using JavaScript/Node.js
│   └── (JavaScript test programs)
│
├── nio_store/              # Encryption state persistence
│   └── (matrix-nio encrypted state storage)
│
└── venv/                   # Python virtual environment
```

## Quick Start

### Prerequisites

- Python 3.7+
- A running Synapse Matrix homeserver (configured at `localhost:8008`)
- matrix-nio library (`pip install matrix-nio`)

### 1. Set Up the Server

The Synapse homeserver should already be configured and running. To verify it's running:

```bash
curl http://localhost:8008/_matrix/client/versions
```

### 2. Register Users and Set Up E2EE

Run the e2etest program suite to test end-to-end encryption:

```bash
cd e2etest

# Step 1: Register two users and setup encryption keys
python3 init.py

# Step 2: Create an encrypted room and invite the second user
python3 setup.py

# Step 3: In one terminal, start receiving messages
python3 recv.py

# Step 4: In another terminal, send an encrypted message
python3 send.py
```

See `e2etest/README.md` for detailed documentation on each program.

### 3. Test with Client Utilities

Register a new user:

```bash
python3 client/register_user.py alice "Alice Smith"
```

Show recent events in a room:

```bash
python3 client/show_events.py '!roomid:localhost' --user-id '@alice:localhost'
```

## Key Concepts

### Matrix Protocol Basics

- **Homeserver**: A server that manages user accounts and room state (Synapse at `localhost:8008`)
- **User ID**: Format `@username:servername` (e.g., `@alice:localhost`)
- **Room ID**: Format `!roomid:servername` (e.g., `!abc123:localhost`)
- **Events**: Messages and state changes that form the immutable history of rooms
- **Sync**: The process of retrieving new events from the server

### End-to-End Encryption (E2EE)

- **Protocol**: Olm/Megolm encryption
- **Device Keys**: Each client device has a unique identity
- **One-Time Keys**: Used to establish initial encrypted sessions
- **Megolm Sessions**: Room-wide symmetric keys for efficient group messaging
- **Storage**: Encryption state persisted in `nio_store/` directory

## Client Library

This project uses **matrix-nio**, a modern async Python library for Matrix:

- **Advantages**: Modern async/await syntax, active development, comprehensive E2EE support
- **Documentation**: https://matrix-nio.readthedocs.io/
- **Source**: https://github.com/poljar/matrix-nio

## Project Structure Details

### Server Configuration

The `server/` directory contains a Synapse Matrix homeserver setup:
- Configured to listen on `localhost:8008`
- SQLite database for persistence
- Registration enabled for testing
- Logging configuration for debugging

### Client Programs

**Core Utilities** (`client/`):
- `register_user.py`: Registers a new user with a generated password hash
- `sync_and_invite.py`: Handles syncing with the server and sending invitations
- `show_events.py`: Displays recent events in a room
- `encryption.py`: Helper functions for E2EE operations

**E2EE Test Suite** (`e2etest/`):
- `init.py`: Creates two test users with encryption keys
- `setup.py`: Creates an encrypted room and manages invitations
- `send.py`: Sends encrypted messages
- `recv.py`: Receives and decrypts messages

### Encryption Storage

The `nio_store/` directory persists encryption state between runs:
- Device identities
- Encryption keys
- Trust relationships
- Session state

**Important**: Do not delete this directory between send/recv runs, as it breaks the encryption trust chain.

## Development and Testing

### Run Tests

```bash
python3 client/test_e2e.py
```

### View Server Logs

```bash
tail -f server/logs/*.log
```

### Check Server Status

```bash
curl http://localhost:8008/_synapse/admin/v1/users
```

## Learning Path

1. **Start Simple**: Use `register_user.py` to understand basic user registration
2. **Explore Events**: Use `show_events.py` to see the event model
3. **Sync Operations**: Study `sync_and_invite.py` to understand the sync API
4. **E2EE Basics**: Run `e2etest/init.py` and examine how encryption keys are created
5. **Encrypted Messaging**: Complete the send/recv cycle to see E2EE in action
6. **Inspect State**: Look at `userconfig.json` and `roomconfig.json` to see the data model

## Documentation

- **Server Config**: See `server/homeserver.yaml` for Synapse configuration
- **E2EE Details**: See `e2etest/README.md` for comprehensive E2EE test documentation
- **Encryption Logic**: See `client/encryption.py` for E2EE implementation details
- **CLAUDE.md**: Project rules and guidelines for development

## Troubleshooting

### Server not responding

Check if Synapse is running:
```bash
ps aux | grep synapse
```

Start it if needed:
```bash
python -m synapse.app.homeserver --config-path server/homeserver.yaml
```

### E2EE Decryption failures

- Ensure `nio_store/` directory is not deleted between send/recv runs
- Check that both users have completed the `init.py` setup
- Verify device trust by checking the logs in `recv.py`

### User registration fails

- Check that the server is accessible at `localhost:8008`
- Ensure the username is not already registered
- Try with a unique username format: `user_XXXXX`

## Notes

- Each `init.py` run creates new users with random usernames
- Multiple test runs can coexist without conflicts
- Messages are fully encrypted end-to-end; the server cannot read them
- Device verification is automatic in tests; production requires explicit verification
- The `nio_store/` directory must not be deleted between send/recv runs

## Related Resources

- [Matrix Specification](https://spec.matrix.org/)
- [matrix-nio Documentation](https://matrix-nio.readthedocs.io/)
- [Synapse Documentation](https://matrix-org.github.io/synapse/)
- [End-to-End Encryption Guide](https://spec.matrix.org/latest/client-server-api/#end-to-end-encryption)

## License

This project is for educational purposes and learning the Matrix protocol.
