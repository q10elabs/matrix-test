#!/usr/bin/env node

/**
 * Send an encrypted message in the E2EE test room.
 *
 * This program:
 * 1. Loads alice's credentials and room config
 * 2. Logs in with E2EE support
 * 3. Processes pending events (syncs)
 * 4. Sends an encrypted message to the test room
 * 5. Waits briefly to process further events
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

async function main(): Promise<number> {
  logger.section("Matrix E2EE Test: Send Message");

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
  if (users.length < 1) {
    logger.error("✗ No users in configuration");
    return 1;
  }

  const alice = users[0]; // First user is sender
  const roomId = roomConfig.room_id;

  logger.info("");
  logger.info(`Sender: ${alice.user_id}`);
  logger.info(`Room:   ${roomId}`);

  // Create and login client
  logger.info("");
  logger.info(`Creating client for ${alice.user_id}`);

  const client = sdk.createClient({
    baseUrl: SERVER_URL,
    userId: alice.user_id,
    deviceId: alice.device_id,
    store: new sdk.MemoryStore(),
  });

  try {
    // Initialize crypto
    logger.info(`Initializing crypto for ${alice.user_id}`);
    await client.initCrypto();
    logger.info(`✓ Crypto initialized for ${alice.user_id}`);

    // Login
    logger.info(`Logging in as ${alice.user_id}`);
    const loginResponse = await client.login("m.login.password", {
      user: alice.username,
      password: alice.password,
    });
    logger.info(`✓ Logged in as ${alice.user_id}`);

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

    // Join the room
    logger.info("");
    logger.info(`Joining room ${roomId}`);
    const joinedRoom = await client.joinRoom(roomId);
    logger.info(`✓ Joined room`);

    // Wait a bit for room state to settle
    await new Promise((resolve) => setTimeout(resolve, 1000));

    // Mark other users' devices as trusted for E2E
    logger.info("Marking devices as trusted for E2E encryption...");
    try {
      const crypto_module = client.getCrypto();
      if (crypto_module) {
        const room = client.getRoom(roomId);
        if (room) {
          const members = room.getJoinedMembers();
          for (const member of members) {
            if (member.userId !== alice.user_id) {
              try {
                const devices = await crypto_module.getUserDeviceInfo([member.userId]);
                for (const [deviceId, deviceInfo] of Object.entries(devices.get(member.userId) || {})) {
                  try {
                    await crypto_module.markDeviceAsVerified(member.userId, deviceId);
                    logger.debug(`  Marked ${deviceId} from ${member.userId} as trusted`);
                  } catch (error) {
                    logger.debug(`  Could not mark device: ${error}`);
                  }
                }
              } catch (error) {
                logger.debug(`  Could not get devices: ${error}`);
              }
            }
          }
        }
      }
    } catch (error) {
      logger.warn(`⚠ Failed to verify devices: ${error}`);
    }

    // Send encrypted message
    logger.info("");
    const message = `Hello from alice at ${new Date().toISOString()}!`;
    logger.info(`Sending encrypted message to ${roomId}`);
    logger.info(`Message: ${message}`);

    try {
      const response = await client.sendTextMessage(roomId, message);
      logger.info(`✓ Message sent successfully`);
      logger.info(`  Event ID: ${response.event_id}`);
    } catch (error) {
      logger.error(`✗ Failed to send message: ${error}`);
      await client.stopClient();
      return 1;
    }

    // Wait for further events
    logger.info("");
    logger.info(`Waiting 5 seconds to process further events...`);
    await new Promise((resolve) => setTimeout(resolve, 5000));

    await client.stopClient();

    logger.info("");
    logger.section("✓ Send complete!");

    return 0;
  } catch (error) {
    logger.error(`✗ Exception during send: ${error}`);
    try {
      await client.stopClient();
    } catch (e) {
      // ignore
    }
    return 1;
  }
}

main().then((code) => process.exit(code));
