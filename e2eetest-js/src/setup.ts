#!/usr/bin/env node

/**
 * Setup E2EE test by creating an encrypted room and inviting the second user.
 *
 * This program:
 * 1. Loads alice's credentials from userconfig.json
 * 2. Logs in with E2EE support
 * 3. Creates a new room with encryption enabled
 * 4. Invites bob to the room
 * 5. Saves room details to roomconfig.json
 *
 * The roomconfig.json file is used by send.ts and recv.ts.
 */

import * as crypto from "crypto";
import { logger } from "./utils/logger.js";
import {
  loadUserConfig,
  saveRoomConfig,
  RoomConfig,
} from "./utils/config.js";
import {
  createAndLoginClient,
  syncClient,
  closeClient,
} from "./utils/client.js";

function generateRandomRoomName(): string {
  const randomSuffix = crypto.randomBytes(3).toString("hex").slice(0, 5);
  return `room_${randomSuffix}`;
}

async function main(): Promise<number> {
  logger.section("Matrix E2EE Test: Room Setup");

  // Load configurations
  logger.info("");
  const userConfig = await loadUserConfig();
  if (!userConfig) {
    return 1;
  }

  const users = userConfig.users;
  if (users.length < 2) {
    logger.error("✗ Need at least 2 users in configuration");
    return 1;
  }

  const alice = users[0]; // First user is room creator
  const bob = users[1]; // Second user to invite

  logger.info("");
  logger.info(`Creator: ${alice.user_id}`);
  logger.info(`Invitee: ${bob.user_id}`);

  // Login as alice
  logger.info("");
  const client = await createAndLoginClient(
    alice.user_id,
    alice.password,
    alice.device_id
  );
  if (!client) {
    logger.error("✗ Failed to login as alice");
    return 1;
  }

  // Sync to establish state
  logger.info("");
  if (!(await syncClient(client))) {
    logger.error("✗ Failed to sync");
    await closeClient(client);
    return 1;
  }

  // Create encrypted room
  logger.info("");
  const roomName = generateRandomRoomName();
  logger.info(`Creating encrypted room: ${roomName}`);

  try {
    const roomInfo = await client.createRoom({
      name: roomName,
      initial_state: [
        {
          type: "m.room.encryption",
          state_key: "",
          content: {
            algorithm: "m.megolm.v1.aes-sha2",
          },
        },
      ],
    });

    const roomId = roomInfo.room_id;
    logger.info(`✓ Created encrypted room: ${roomId}`);

    // Invite bob
    logger.info("");
    logger.info(`Inviting ${bob.user_id} to ${roomId}`);

    try {
      await client.invite(roomId, bob.user_id);
      logger.info(`✓ Invited ${bob.user_id} to room`);
    } catch (error) {
      logger.error(`✗ Failed to invite ${bob.user_id}: ${error}`);
      await closeClient(client);
      return 1;
    }

    // Save room config
    logger.info("");
    const roomConfig: RoomConfig = {
      room_id: roomId,
      room_name: roomName,
      created_at: new Date().toISOString(),
      creator: alice.user_id,
    };

    if (!(await saveRoomConfig(roomConfig))) {
      logger.error("Failed to save room configuration");
      await closeClient(client);
      return 1;
    }

    // Cleanup
    await closeClient(client);

    logger.info("");
    logger.section("✓ Setup complete!");
    logger.info("Room configuration saved to: roomconfig.json");
    logger.info("");
    logger.info("Next steps:");
    logger.info("  1. In one terminal: yarn send");
    logger.info("  2. In another terminal: yarn recv");

    return 0;
  } catch (error) {
    logger.error(`✗ Exception during setup: ${error}`);
    await closeClient(client);
    return 1;
  }
}

main().then((code) => process.exit(code));
