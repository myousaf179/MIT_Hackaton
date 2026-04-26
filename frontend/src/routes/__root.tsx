import {
  Outlet,
  Link,
  createRootRoute,
  HeadContent,
  Scripts,
} from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Toaster } from "@/components/ui/sonner";

import appCss from "../styles.css?url";

function NotFoundComponent() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="text-7xl font-bold text-foreground">404</h1>
        <h2 className="mt-4 text-xl font-semibold text-foreground">
          Page not found
        </h2>
        <p className="mt-2 text-sm text-muted-foreground">
          The page you're looking for doesn't exist or has been moved.
        </p>
        <div className="mt-6">
          <Link
            to="/"
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Go home
          </Link>
        </div>
      </div>
    </div>
  );
}

export const Route = createRootRoute({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      { title: "UNMAPPED — Map invisible skills into AI-ready credentials" },
      {
        name: "description",
        content:
          "Translate informal skills into ISCO/ESCO-aligned, portable credentials calibrated for LMIC labour markets. World Bank UNMAPPED hackathon.",
      },
      { name: "author", content: "UNMAPPED" },
      { property: "og:title", content: "UNMAPPED — Skills, mapped." },
      {
        property: "og:description",
        content:
          "Translate informal skills into portable, ISCO/ESCO-aligned credentials, calibrated for your local labour market.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
      { name: "twitter:site", content: "@Lovable" },
    ],
    links: [
      {
        rel: "stylesheet",
        href: appCss,
      },
    ],
  }),
  shellComponent: RootShell,
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
});

function RootShell({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <HeadContent />
      </head>
      <body>
        {children}
        <Scripts />
      </body>
    </html>
  );
}

function RootComponent() {
  useServiceWorker();
  const offline = useOnlineStatus();

  return (
    <>
      {offline && (
        <div
          role="status"
          aria-live="polite"
          className="sticky top-0 z-50 bg-amber-500 text-amber-950 text-xs sm:text-sm text-center py-2 px-3 font-medium"
        >
          You appear to be offline. Showing the most recent cached results — new
          analyses will run when you reconnect.
        </div>
      )}
      <Outlet />
      <Toaster richColors position="top-right" />
    </>
  );
}

function useServiceWorker() {
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!("serviceWorker" in navigator)) return;
    if (import.meta.env.DEV) return;

    const onLoad = () => {
      navigator.serviceWorker
        .register("/service-worker.js", { scope: "/" })
        .then((registration) => {
          registration.addEventListener("updatefound", () => {
            const installing = registration.installing;
            if (!installing) return;
            installing.addEventListener("statechange", () => {
              if (
                installing.state === "installed" &&
                navigator.serviceWorker.controller
              ) {
                toast.info(
                  "A new version of UNMAPPED is available — refresh to update.",
                );
              }
            });
          });
        })
        .catch(() => {
          /* offline fallback still works without registration */
        });
    };

    if (document.readyState === "complete") onLoad();
    else window.addEventListener("load", onLoad, { once: true });

    return () => window.removeEventListener("load", onLoad);
  }, []);
}

function useOnlineStatus() {
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const update = () => setOffline(!navigator.onLine);
    update();
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);

  return offline;
}
