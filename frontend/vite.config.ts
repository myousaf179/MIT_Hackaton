// @lovable.dev/vite-tanstack-config already includes the following — do NOT add them manually
// or the app will break with duplicate plugins:
//   - tanstackStart, viteReact, tailwindcss, tsConfigPaths, cloudflare (build-only),
//     componentTagger (dev-only), VITE_* env injection, @ path alias, React/TanStack dedupe,
//     error logger plugins, and sandbox detection (port/host/strictPort).
// You can pass additional config via defineConfig({ vite: { ... } }) if needed.
import { defineConfig } from "@lovable.dev/vite-tanstack-config";

// Production build is targeted at Vercel as a SPA:
//   * `cloudflare: false` removes the Workers adapter so we don't ship a
//     `wrangler.json` / Worker bundle in the deploy.
//   * `tanstackStart.spa.enabled: true` makes TanStack Start render a static
//     `index.html` shell that the client router hydrates — this pairs with the
//     `/(.*)` -> `/index.html` rewrite configured in `vercel.json`.
//   * `vite.base: "/"` keeps assets at the root (Vercel serves from the apex).
//   * `vite.build.outDir: "dist"` matches the `outputDirectory` in
//     `vercel.json`. The client bundle lands in `dist/client` and the SPA
//     shell is copied to `dist/index.html` by our build script.
export default defineConfig({
  cloudflare: false,
  tanstackStart: {
    spa: {
      enabled: true,
    },
  },
  vite: {
    base: "/",
    build: {
      outDir: "dist",
      emptyOutDir: true,
    },
    // One dev server, stable HMR. Avoids "Failed to fetch dynamically imported
    // module" when a stale 5173 process serves broken cached chunks.
    server: {
      port: 5173,
      strictPort: true,
    },
    optimizeDeps: {
      include: [
        "react",
        "react-dom",
        "react-circular-progressbar",
        "lucide-react",
        "recharts",
        "sonner",
        "@tanstack/react-router",
      ],
    },
  },
});
