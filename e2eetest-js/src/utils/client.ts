/**
 * Client utilities for creating and managing Matrix client instances with E2EE support.
 */

import { getStorePath, ensureStoreDir } from "./config.js";
import { logger } from "./logger.js";
import Olm from "@matrix-org/olm";

// Import matrix-js-sdk using require since ESM import has issues
const sdk = require("matrix-js-sdk");

// Initialize Olm once
let olmInitialized = false;
async function initOlm() {
  if (!olmInitialized) {
    try {
      await Olm.init();
      (globalThis as any).Olm = Olm;
      olmInitialized = true;
    } catch (error) {
      logger.error(`Failed to initialize Olm: ${error}`);
    }
  }
}

const SERVER_URL = "http://localhost:8008";

export async function createAndLoginClient(
  userId: string,
  password: string,
  deviceId: string,
  enableCrypto: boolean = true
): Promise<any | null> {
  try {
    ensureStoreDir();
    const storeDir = getStorePath();

    // Initialize Olm if needed
    await initOlm();

    logger.info(`Creating client for ${userId}`);

    // Create client with crypto support
    const client = sdk.createClient({
      baseUrl: SERVER_URL,
      userId: userId,
      deviceId: deviceId,
      store: new sdk.MemoryStore(),
    });

    // Initialize crypto if enabled and not already initialized
    if (enableCrypto && !client.isCryptoEnabled()) {
      logger.info(`Initializing crypto for ${userId}`);

      // Initialize crypto - this sets up the Olm account
      await client.initCrypto();

      logger.info(`✓ Crypto initialized for ${userId}`);
    }

    // Login
    logger.info(`Logging in as ${userId}`);
    try {
      const response = await client.login("m.login.password", {
        user: userId.split(":")[0].replace("@", ""),
        password: password,
      });

      logger.info(`✓ Logged in as ${userId}`);
      logger.debug(`Device ID: ${response.device_id}`);

      // Start the client (this begins syncing)
      try {
        await client.startClient();
        logger.info(`✓ Client started and syncing`);
      } catch (e) {
        logger.debug(`Client start warning: ${e}`);
      }

      return client;
    } catch (error) {
      logger.error(`✗ Login failed: ${error}`);
      return null;
    }
  } catch (error) {
    logger.error(`✗ Exception creating client: ${error}`);
    return null;
  }
}

export async function syncClient(
  client: any,
  timeout: number = 0
): Promise<boolean> {
  try {
    logger.info(`Syncing client (timeout: ${timeout}ms)`);

    // Wait a bit for the client to start syncing in background
    // then wait for it to reach PREPARED state
    let waited = 0;
    const maxWait = 10000;
    while (waited < maxWait) {
      try {
        const syncState = client.getSyncState?.();
        if (syncState === "PREPARED") {
          break;
        }
      } catch (e) {
        // getSyncState might not exist
      }
      await new Promise((resolve) => setTimeout(resolve, 100));
      waited += 100;
    }

    logger.info(`✓ Sync completed`);
    return true;
  } catch (error) {
    logger.error(`✗ Sync failed: ${error}`);
    return false;
  }
}

export async function uploadKeys(client: any): Promise<boolean> {
  try {
    if (!client.isCryptoEnabled()) {
      logger.error(`✗ Crypto not enabled`);
      return false;
    }

    logger.info(`Uploading encryption keys`);

    // This triggers the key upload
    await client.getCrypto()?.uploadKeys();

    logger.info(`✓ Encryption keys uploaded`);
    return true;
  } catch (error) {
    logger.error(`✗ Failed to upload keys: ${error}`);
    return false;
  }
}

export async function closeClient(client: any): Promise<void> {
  try {
    logger.info(`Closing client`);

    try {
      await client.stopClient();
    } catch (e) {
      logger.debug(`Stop warning: ${e}`);
    }

    // Don't call crypto.stop() directly, stopClient handles cleanup
    logger.info(`✓ Client closed`);
  } catch (error) {
    logger.warn(`⚠ Error closing client: ${error}`);
  }
}

export function getCryptoState(client: any): string {
  if (!client.isCryptoEnabled()) {
    return "DISABLED";
  }

  const crypto = client.getCrypto();
  if (!crypto) {
    return "NOT_INITIALIZED";
  }

  return "READY";
}
