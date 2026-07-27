import type { User } from "./auth.ts";

// Augments Hono's context so c.get("user") / c.set("user", …) are typed.
// This file only needs to be part of the compilation to take effect globally.
declare module "hono" {
  interface ContextVariableMap {
    user: User;
  }
}

export {};
