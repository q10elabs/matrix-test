# Add --no-load-token Flag to sync_and_invite.py

## Task Specification
Add a new command-line flag `--no-load-token` to the sync_and_invite.py script that skips loading the sync token from the server, forcing the client to sync from the beginning rather than resuming from the last known position.

## High-Level Decisions
- Flag name: `--no-load-token` (parallel naming convention to existing `--no-save-token`)
- Implementation approach: Add argparse argument and conditionally skip `get_sync_token_from_server()` call
- Behavior: When flag is set, sync_token is None, causing sync to start fresh

## Files Modified
- `client/sync_and_invite.py`: Added `--no-load-token` argument and logic to skip token loading

## Implementation Summary
1. Added `--no-load-token` argument to argparse with descriptive help text
2. Extract flag from parsed arguments in main()
3. Conditionally skip `get_sync_token_from_server()` call when flag is set
4. Updated docstring examples and epilog to show usage

## Current Status
Completed. The `--no-load-token` flag now allows users to skip loading the sync token and force a fresh sync from the beginning.
