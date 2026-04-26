// @lovable.dev/vite-tanstack-config already includes the following — do NOT add them manually
// or the app will break with duplicate plugins:
//   - tanstackStart, viteReact, tailwindcss, tsConfigPaths, cloudflare (build-only),
//     componentTagger (dev-only), VITE_* env injection, @ path alias, React/TanStack dedupe,
//     error logger plugins, and sandbox detection (port/host/strictPort).
// You can pass additional config via defineConfig({ vite: { ... } }) if needed.
import { defineConfig } from "@lovable.dev/vite-tanstack-config";

export default defineConfig({
  // Disable the Cloudflare Workers adapter so the build produces a regular
  // static client bundle suitable for Vercel (and any other static host).
  cloudflare: false,
  // Build the app as an SPA — TanStack Start emits a real `index.html` that
  // Vercel can serve and rewrite all routes to.
  tanstackStart: {
    spa: { enabled: true },
  },
  vite: {
    // Served from the domain root on Vercel. Override via VITE_BASE_URL if you need
    // to host the app under a sub-path (e.g. "/app/").
    base: process.env.VITE_BASE_URL ?? "/",
    build: {
      outDir: "dist",
      emptyOutDir: true,
      sourcemap: false,
    },
  },
});
