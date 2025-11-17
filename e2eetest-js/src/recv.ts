#!/usr/bin/env node

/**
 * Receive and decrypt encrypted messages in the E2EE test room.
 *
 * This program:
 * 1. Loads bob's credentials and room config
 * 2. Logs in with E2EE support
 * 3. Processes pending events (accepts room invites)
 * 4. Syncs continuously, waiting for and decrypting incoming messages
 * 5. Logs all received messages with decryption status
 */

import { logger } from "./utils/logger.js";

// Import matrix-js-sdk using require since ESM import has issues
const sdk = require("matrix-js-sdk");
import {
  loadUserConfig,
  loadRoomConfig,
} from "./utils/config.js";
import Olm from "@matrix-org/olm";

const SERVER_URL = "http://localhost:8008";

let shutdownRequested = false;

function handleShutdown(): void {
  logger.info("");
  logger.info("Shutdown signal received");
  shutdownRequested = true;
}

async function main(): Promise<number> {
  logger.section("Matrix E2EE Test: Receive Messages");

  // Setup signal handlers for graceful shutdown
  process.on("SIGINT", handleShutdown);
  process.on("SIGTERM", handleShutdown);

  // Initialize Olm
  logger.info("Initializing Olm for E2EE support...");
  try {
    await Olm.init();
    (globalThis as any).Olm = Olm;
    logger.info("✓ Olm initialized");
  } catch (error) {
    logger.error(`✗ Failed to initialize Olm: ${error}`);
    return 1;
  }

  // Load configurations
  logger.info("");
  const userConfig = await loadUserConfig();
  if (!userConfig) {
    return 1;
  }

  const roomConfig = await loadRoomConfig();
  if (!roomConfig) {
    return 1;
  }

  const users = userConfig.users;
  if (users.length < 2) {
    logger.error("✗ Need at least 2 users in configuration");
    return 1;
  }

  const bob = users[1]; // Second user is receiver
  const roomId = roomConfig.room_id;

  logger.info("");
  logger.info(`Receiver: ${bob.user_id}`);
  logger.info(`Room:     ${roomId}`);

  // Create and login client
  logger.info("");
  logger.info(`Creating client for ${bob.user_id}`);

  const client = sdk.createClient({
    baseUrl: SERVER_URL,
    userId: bob.user_id,
    deviceId: bob.device_id,
    store: new sdk.MemoryStore(),
  });

  try {
    // Initialize crypto
    logger.info(`Initializing crypto for ${bob.user_id}`);
    await client.initCrypto();
    logger.info(`✓ Crypto initialized for ${bob.user_id}`);

    // Login
    logger.info(`Logging in as ${bob.user_id}`);
    const loginResponse = await client.login("m.login.password", {
      user: bob.username,
      password: bob.password,
    });
    logger.info(`✓ Logged in as ${bob.user_id}`);

    // Start client for sync
    await client.startClient();
    logger.info(`✓ Client started`);

    // Wait for initial sync
    logger.info(`Waiting for initial sync...`);
    let waited = 0;
    while (waited < 10000) {
      const syncState = client.getSyncState?.();
      if (syncState === "PREPARED") {
        break;
      }
      await new Promise((resolve) => setTimeout(resolve, 100));
      waited += 100;
    }
    logger.info(`✓ Initial sync complete`);

    // Process pending invites
    logger.info("");
    logger.info("Processing pending events and invites...");

    const rooms = client.getRooms();
    const joinedRooms = rooms.filter((room) => {
      try {
        return client.getRoom(room.roomId)?.getMyMembership() === "join";
      } catch {
        return false;
      }
    }).length;
    const invitedRooms = rooms.filter((room) => {
      try {
        return client.getRoom(room.roomId)?.getMyMembership() === "invite";
      } catch {
        return false;
      }
    }).length;

    logger.info(`✓ Sync completed`);
    logger.info(`  Joined rooms: ${joinedRooms}`);
    logger.info(`  Invited rooms: ${invitedRooms}`);

    // Auto-join any invited rooms
    if (invitedRooms > 0) {
      logger.info("Accepting room invitations...");
      for (const room of rooms) {
        try {
          const membership = client.getRoom(room.roomId)?.getMyMembership();
          if (membership === "invite") {
            try {
              await client.joinRoom(room.roomId);
              logger.info(`  ✓ Accepted invite to ${room.roomId}`);
            } catch (error) {
              logger.error(`  ✗ Failed to accept invite to ${room.roomId}: ${error}`);
            }
          }
        } catch (error) {
          logger.debug(`  Could not check room: ${error}`);
        }
      }
    }

    // Setup event listeners for messages
    let messageCount = 0;
    const receivedEvents = new Set<string>();

    function messageCallback(event: any): void {
      // Only process room messages
      if (event.getType() !== "m.room.message") {
        return;
      }

      // Avoid processing the same event twice
      const eventId = event.getId();
      if (receivedEvents.has(eventId)) {
        return;
      }
      receivedEvents.add(eventId);

      const content = event.getContent();
      const sender = event.getSender();
      const timestamp = event.getTs();
      const body = content.body || "(empty)";

      messageCount++;

      // Determine if message was successfully decrypted
      // If it's currently encrypted (isEncrypted() is true), it means decryption failed
      // If it's not encrypted (isEncrypted() is false), it was decrypted or is plaintext
      const wasEncryptedButDecrypted = !event.isEncrypted() && event.getRawContent().algorithm;
      const status = event.isEncrypted() ? "✗ ENCRYPTED (failed to decrypt)" : "✓ DECRYPTED";

      logger.info(`[Message #${messageCount}] ${status}`);
      logger.info(`  Event ID: ${eventId}`);
      logger.info(`  From: ${sender}`);
      logger.info(
        `  Time: ${new Date(timestamp).toISOString()}`
      );
      logger.info(`  Body: ${body}`);
    }

    client.on("Room.timeline", messageCallback);

    // Wait for messages
    logger.info("");
    logger.info(`Waiting for messages in ${roomId}...`);
    logger.info(`(Will wait up to 40 seconds for decryption)`);
    logger.info("");

    const startTime = Date.now();
    const endTime = startTime + 40 * 1000;

    while (Date.now() < endTime && !shutdownRequested) {
      await new Promise((resolve) => setTimeout(resolve, 500));
    }

    if (!shutdownRequested) {
      logger.info("Timeout reached (40s)");
    }

    await client.stopClient();

    logger.info("");
    logger.section("✓ Receive complete!");
    if (messageCount === 0) {
      logger.info("⚠ No messages received during wait period");
    } else {
      logger.info(`✓ Received and processed ${messageCount} message(s)`);
    }

    return 0;
  } catch (error) {
    logger.error(`✗ Exception during receive: ${error}`);
    try {
      await client.stopClient();
    } catch (e) {
      // ignore
    }
    return 1;
  }
}

main().then((code) => process.exit(code));
