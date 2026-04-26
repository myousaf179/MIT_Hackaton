// @lovable.dev/vite-tanstack-config already includes the following — do NOT add them manually
// or the app will break with duplicate plugins:
//   - tanstackStart, viteReact, tailwindcss, tsConfigPaths, cloudflare (build-only),
//     componentTagger (dev-only), VITE_* env injection, @ path alias, React/TanStack dedupe,
//     error logger plugins, and sandbox detection (port/host/strictPort).
// You can pass additional config via defineConfig({ vite: { ... } }) if needed.
import { defineConfig } from "@lovable.dev/vite-tanstack-config";

// Backend URL for the UNMAPPED hackathon. The dev server proxies `/api/*`
// to this origin so the browser does not need to deal with CORS during local
// development. In production builds the app talks to the backend directly via
// `VITE_API_BASE` (see `src/api.ts`).
const BACKEND_URL =
  process.env.VITE_BACKEND_URL ?? "https://unmapped-backend.onrender.com";

export default defineConfig({
  vite: {
    server: {
      proxy: {
        "/api": {
          target: BACKEND_URL,
          changeOrigin: true,
          secure: true,
          rewrite: (path) => path.replace(/^\/api/, ""),
        },
      },
    },
  },
});
