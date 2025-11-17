# Task description

Generate 3 programs 'init', 'setup', 'send', 'recv' in the directory 'e2etest'.

- program 'init' registers two users, sets up their device E2EE keys (including upload to the server).
- program 'setup' logs in as first user, creates a new room with E2EE, invites 2nd user to the room.
- program 'send' logs in as first user, processes pending events, then sends an encrypted message to the room, then waits to process further events.
- program 'recv' logs in as 2nd user, processes pending events (including invites), then waits to process further events including decrypting messages.

Make 'init' write the usernames and passwords to a shared 'userconfig' file, loaded by the other programs.
Make 'setup' write the room details to a shared 'roomconfig' file, loaded by the programs 'send' and 'recv'.

You can use the pre-existing Matrix server running at http://localhost:8008.

Use online sources to understand the matrix protocol, as well as the source code for tests and examples here:

- /home/kena/src/matrix-nio/tests
- /home/kena/src/matrix-nio/examples
