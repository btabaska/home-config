import { randomUUID, randomBytes } from "node:crypto";

export const uuid = (): string => randomUUID();

const ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"; // no ambiguous chars

export function shortCode(len = 5): string {
  const bytes = randomBytes(len);
  let out = "";
  for (let i = 0; i < len; i++) out += ALPHABET[bytes[i] % ALPHABET.length];
  return out;
}

// Share slug like "48-kx7q2" — the visible drop id plus a random suffix.
export function dropSlug(dropId: number): string {
  return `${dropId}-${shortCode(5)}`;
}

export const now = (): number => Date.now();
