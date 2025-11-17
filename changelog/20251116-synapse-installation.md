# Synapse Server Installation - 2025-11-16

## Task Specification
Install and configure a Synapse Matrix server for local testing.

**Requirements:**
- Install Synapse as a Python module
- Create Python virtual environment in `venv/` subdirectory
- Place all server configuration in `server/` directory
- Use SQLite for storage
- Federation: disabled (local only)
- Server domain: localhost
- Security features: disabled (for testing/development)

**Sources:**
- GitHub: https://github.com/element-hq/synapse
- Installation docs: https://element-hq.github.io/synapse/latest/setup/installation.html

## Implementation Plan

1. **Environment Setup**
   - Create Python virtual environment in `venv/`
   - Activate venv
   - Upgrade pip, setuptools, and wheel

2. **Synapse Installation**
   - Install synapse[all] package via pip (includes all optional dependencies)

3. **Server Configuration**
   - Generate base Synapse config with `synctl generate-config`
   - Place config in `server/` directory
   - Configure for localhost, SQLite backend
   - Disable federation
   - Disable rate limiting and security features (for testing)

4. **Verification**
   - Test that Synapse can start without errors
   - Confirm configuration is valid

## Files Modified
- Created: `venv/` - Python virtual environment
- Created: `server/homeserver.yaml` - Main Synapse configuration
- Created: `server/log.yaml` - Logging configuration
- Created: `server/homeserver.db` - SQLite database (auto-created on first run)
- Created: `server/localhost.signing.key` - Server signing key (auto-created on first run)
- Created: `server/media_store/` - Media storage directory

## Current Status
Installation complete and verified. Synapse server successfully starts and listens on:
- 127.0.0.1:8008
- [::1]:8008 (IPv6 localhost)
- 192.168.2.20:8008

Server is configured for:
- Local-only operation (federation disabled)
- SQLite storage
- Open registration without verification
- No rate limiting (for testing)
- No TLS (for local testing)
