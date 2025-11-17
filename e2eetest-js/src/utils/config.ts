/**
 * Configuration file utilities for loading and saving user and room configurations.
 */

import * as fs from "fs";
import * as path from "path";
import { logger } from "./logger.js";

const SCRIPT_DIR = path.dirname(import.meta.url.replace("file://", ""));
const CONFIG_DIR = path.join(SCRIPT_DIR, "../..");

export interface UserInfo {
  username: string;
  password: string;
  user_id: string;
  device_id: string;
  registered_at: string;
}

export interface UserConfig {
  users: UserInfo[];
}

export interface RoomConfig {
  room_id: string;
  room_name: string;
  created_at: string;
  creator: string;
}

export async function loadUserConfig(): Promise<UserConfig | null> {
  const configPath = path.join(CONFIG_DIR, "userconfig.json");
  logger.info(`Loading configuration from ${configPath}`);

  try {
    if (!fs.existsSync(configPath)) {
      logger.error(`✗ ${configPath} not found. Run init first.`);
      return null;
    }

    const content = fs.readFileSync(configPath, "utf-8");
    const config = JSON.parse(content);
    logger.info(`✓ Loaded ${config.users.length} users`);
    return config;
  } catch (error) {
    logger.error(`✗ Failed to load config: ${error}`);
    return null;
  }
}

export async function saveUserConfig(config: UserConfig): Promise<boolean> {
  const configPath = path.join(CONFIG_DIR, "userconfig.json");
  logger.info(`Saving configuration to ${configPath}`);

  try {
    fs.writeFileSync(configPath, JSON.stringify(config, null, 2), "utf-8");
    logger.info(`✓ Saved ${config.users.length} users to ${configPath}`);
    return true;
  } catch (error) {
    logger.error(`✗ Failed to save config: ${error}`);
    return false;
  }
}

export async function loadRoomConfig(): Promise<RoomConfig | null> {
  const configPath = path.join(CONFIG_DIR, "roomconfig.json");
  logger.info(`Loading room config from ${configPath}`);

  try {
    if (!fs.existsSync(configPath)) {
      logger.error(`✗ ${configPath} not found. Run setup first.`);
      return null;
    }

    const content = fs.readFileSync(configPath, "utf-8");
    const config = JSON.parse(content);
    logger.info(`✓ Loaded room config`);
    return config;
  } catch (error) {
    logger.error(`✗ Failed to load room config: ${error}`);
    return null;
  }
}

export async function saveRoomConfig(config: RoomConfig): Promise<boolean> {
  const configPath = path.join(CONFIG_DIR, "roomconfig.json");
  logger.info(`Saving room config to ${configPath}`);

  try {
    fs.writeFileSync(configPath, JSON.stringify(config, null, 2), "utf-8");
    logger.info(`✓ Saved room config to ${configPath}`);
    return true;
  } catch (error) {
    logger.error(`✗ Failed to save room config: ${error}`);
    return false;
  }
}

export function getUserByName(
  config: UserConfig,
  username: string
): UserInfo | undefined {
  return config.users.find((user) => user.username === username);
}

export function getStorePath(): string {
  return path.join(CONFIG_DIR, "store");
}

export function ensureStoreDir(): void {
  const storeDir = getStorePath();
  if (!fs.existsSync(storeDir)) {
    fs.mkdirSync(storeDir, { recursive: true });
  }
}
