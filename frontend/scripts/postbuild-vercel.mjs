// Reshape the TanStack Start build output into the layout Vercel expects:
//   dist/
//     index.html
//     assets/...
// The Lovable preset emits dist/client/* (with _shell.html) and dist/server/*.
// For an SPA deploy on Vercel we only need the static client assets, served
// from dist/ with all routes rewritten to /index.html (see vercel.json).
import { existsSync, rmSync, renameSync, readdirSync, statSync, cpSync } from "node:fs";
import { join, resolve } from "node:path";

const root = resolve(process.cwd(), "dist");
const clientDir = join(root, "client");
const serverDir = join(root, "server");

if (!existsSync(clientDir)) {
  console.warn("[postbuild-vercel] dist/client not found — nothing to reshape.");
  process.exit(0);
}

for (const entry of readdirSync(clientDir)) {
  const from = join(clientDir, entry);
  const to = join(root, entry);
  if (existsSync(to)) rmSync(to, { recursive: true, force: true });
  if (statSync(from).isDirectory()) {
    cpSync(from, to, { recursive: true });
    rmSync(from, { recursive: true, force: true });
  } else {
    renameSync(from, to);
  }
}
rmSync(clientDir, { recursive: true, force: true });

if (existsSync(serverDir)) {
  rmSync(serverDir, { recursive: true, force: true });
}

const shell = join(root, "_shell.html");
const index = join(root, "index.html");
if (existsSync(shell)) {
  if (existsSync(index)) rmSync(index);
  renameSync(shell, index);
}

console.log("[postbuild-vercel] dist/ flattened; index.html ready for Vercel.");
