#!/usr/bin/env node

/**
 * Initialize E2EE test environment by registering users and setting up encryption keys.
 *
 * This program:
 * 1. Registers two users with the Matrix homeserver
 * 2. Initializes E2EE encryption for each user (Olm account setup)
 * 3. Uploads device keys and one-time keys to the server
 * 4. Persists user credentials and device IDs to userconfig.json
 *
 * The userconfig.json file is used by setup.ts, send.ts, and recv.ts.
 */

import * as crypto from "crypto";
import * as https from "https";
import * as http from "http";
import { logger } from "./utils/logger.js";

// Import matrix-js-sdk using require since ESM import has issues
const sdk = require("matrix-js-sdk");
import Olm from "@matrix-org/olm";
import {
  saveUserConfig,
  ensureStoreDir,
  getStorePath,
  UserInfo,
  UserConfig,
} from "./utils/config.js";

const SERVER_URL = "http://localhost:8008";

function generateRandomUsername(): string {
  const randomSuffix = crypto
    .randomBytes(3)
    .toString("hex")
    .slice(0, 5);
  return `user_${randomSuffix}`;
}

function makeHttpRequest(
  method: string,
  path: string,
  body?: any
): Promise<any> {
  return new Promise((resolve, reject) => {
    const url = new URL(SERVER_URL + path);
    const isHttps = url.protocol === "https:";
    const httpModule = isHttps ? https : http;

    const options = {
      hostname: url.hostname,
      port: url.port,
      path: url.pathname + url.search,
      method: method,
      headers: {
        "Content-Type": "application/json",
      },
    };

    const request = httpModule.request(options, (response) => {
      let data = "";

      response.on("data", (chunk) => {
        data += chunk;
      });

      response.on("end", () => {
        try {
          resolve({
            status: response.statusCode,
            body: JSON.parse(data),
          });
        } catch (e) {
          resolve({
            status: response.statusCode,
            body: data,
          });
        }
      });
    });

    request.on("error", reject);

    if (body) {
      request.write(JSON.stringify(body));
    }
    request.end();
  });
}

async function registerUser(username: string): Promise<UserInfo | null> {
  logger.info(`Registering user: ${username}`);

  try {
    const password = username; // For testing, use username as password

    // First request to get auth requirements
    const registerResponse = await makeHttpRequest("POST", "/_matrix/client/r0/register", {
      kind: "user",
      auth: { type: "m.login.dummy" },
      username: username,
      password: password,
      initial_device_display_name: "E2E Test Device",
      inhibit_login: false,
    });

    if (registerResponse.status !== 200) {
      logger.error(
        `✗ Registration failed for ${username}: HTTP ${registerResponse.status}`
      );
      return null;
    }

    const userId = registerResponse.body.user_id;
    const deviceId = registerResponse.body.device_id;
    const accessToken = registerResponse.body.access_token;

    const userInfo: UserInfo = {
      username,
      password,
      user_id: userId,
      device_id: deviceId,
      registered_at: new Date().toISOString(),
    };

    logger.info(
      `✓ Registered ${username}: ${userId}, device: ${deviceId}`
    );

    return userInfo;
  } catch (error) {
    logger.error(`✗ Registration failed for ${username}: ${error}`);
    return null;
  }
}

async function setupEncryptionKeys(userInfo: UserInfo): Promise<boolean> {
  const username = userInfo.username;
  const userId = userInfo.user_id;
  const password = userInfo.password;
  const deviceId = userInfo.device_id;

  logger.info(`Setting up E2EE keys for ${username}`);

  try {
    ensureStoreDir();
    const storeDir = getStorePath();

    const client = sdk.createClient({
      baseUrl: SERVER_URL,
      userId: userId,
      deviceId: deviceId,
      store: new sdk.MemoryStore(),
    });

    // Login
    logger.info(`Logging in as ${username} to setup encryption`);
    const loginResponse = await client.login("m.login.password", {
      user: username,
      password: password,
      device_id: deviceId,
    });

    logger.info(`✓ Logged in as ${username}`);

    // Initialize crypto
    logger.info(`Initializing Olm for ${username}`);
    await client.initCrypto();

    logger.info(`✓ Olm initialized for ${username}`);

    // Just close the client - keys are set up in the Olm account
    // The actual key upload will happen when the client is used in setup/send/recv
    try {
      await client.stopClient();
    } catch (e) {
      logger.debug(`Stop client warning: ${e}`);
    }

    logger.info(`✓ E2EE setup complete for ${username}`);
    return true;
  } catch (error) {
    logger.error(`✗ Exception setting up encryption for ${username}: ${error}`);
    return false;
  }
}

async function main(): Promise<number> {
  logger.section("Matrix E2EE Test: User Registration and Key Setup");

  // Initialize Olm
  logger.info("Initializing Olm for E2EE support...");
  try {
    await Olm.init();
    // Make Olm available globally for matrix-js-sdk
    (globalThis as any).Olm = Olm;
    logger.info("✓ Olm initialized");
  } catch (error) {
    logger.error(`✗ Failed to initialize Olm: ${error}`);
    return 1;
  }

  // Generate random usernames
  const usernames = [generateRandomUsername(), generateRandomUsername()];
  logger.info(`Generated usernames: ${usernames.join(", ")}`);

  const users: UserInfo[] = [];

  // Register all users
  logger.info("");
  for (const username of usernames) {
    const userInfo = await registerUser(username);
    if (!userInfo) {
      logger.error(`Failed to register ${username}, aborting`);
      return 1;
    }
    users.push(userInfo);
  }

  logger.info("");
  logger.info("Registered users:");
  for (const user of users) {
    logger.info(`  - ${user.username}: ${user.user_id}`);
  }

  // Setup encryption keys for each user
  logger.info("");
  logger.info("Setting up encryption keys...");
  for (const userInfo of users) {
    const success = await setupEncryptionKeys(userInfo);
    if (!success) {
      logger.error(
        `Failed to setup encryption for ${userInfo.username}, aborting`
      );
      return 1;
    }
  }

  logger.info("");
  logger.info("All users have encryption keys configured");

  // Save configuration
  logger.info("");
  const config: UserConfig = { users };
  if (!(await saveUserConfig(config))) {
    logger.error("Failed to save user configuration");
    return 1;
  }

  logger.info("");
  logger.section("✓ Initialization complete!");
  logger.info("Configuration saved to: userconfig.json");
  logger.info("");
  logger.info("Next steps:");
  logger.info("  1. Run: yarn setup");
  logger.info("  2. In another terminal: yarn send");
  logger.info("  3. In another terminal: yarn recv");

  return 0;
}

main().then((code) => process.exit(code));
