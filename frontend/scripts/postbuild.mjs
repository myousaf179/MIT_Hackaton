#!/usr/bin/env node
// Post-build script for Vercel deployment.
//
// TanStack Start's SPA mode emits the rendered shell at
// `dist/client/_shell.html` and ships SSR artifacts under `dist/server/`.
// Vercel only needs static assets, and our `vercel.json` rewrites all routes
// to `/index.html`. So after `vite build` we:
//   1. Promote `dist/client/*` to `dist/*` (so the assets sit at the root of
//      the publish directory).
//   2. Rename the SPA shell `_shell.html` to `index.html`.
//   3. Drop the `dist/server` bundle which Vercel's static hosting does not
//      need.
//
// Keep this script Node-only (no extra deps) so it runs on Vercel build
// images out of the box.
import { existsSync, readdirSync, renameSync, rmSync, statSync } from "node:fs";
import { join } from "node:path";

const root = process.cwd();
const distDir = join(root, "dist");
const clientDir = join(distDir, "client");
const serverDir = join(distDir, "server");

if (!existsSync(distDir)) {
  console.error("[postbuild] dist/ not found — did `vite build` run?");
  process.exit(1);
}

if (existsSync(clientDir)) {
  for (const entry of readdirSync(clientDir)) {
    const from = join(clientDir, entry);
    const to = join(distDir, entry);
    if (existsSync(to)) rmSync(to, { recursive: true, force: true });
    renameSync(from, to);
  }
  rmSync(clientDir, { recursive: true, force: true });
}

const shellPath = join(distDir, "_shell.html");
const indexPath = join(distDir, "index.html");
if (existsSync(shellPath)) {
  if (!existsSync(indexPath)) {
    renameSync(shellPath, indexPath);
  } else {
    rmSync(shellPath, { force: true });
  }
}

if (existsSync(serverDir)) {
  rmSync(serverDir, { recursive: true, force: true });
}

if (!existsSync(indexPath)) {
  console.error(
    "[postbuild] dist/index.html missing after flatten — aborting so Vercel doesn't deploy a broken bundle.",
  );
  process.exit(1);
}

const finalEntries = readdirSync(distDir)
  .map((name) => {
    const stat = statSync(join(distDir, name));
    return `${stat.isDirectory() ? "d" : "f"} ${name}`;
  })
  .join(", ");
console.log(`[postbuild] dist ready for Vercel (${finalEntries})`);
