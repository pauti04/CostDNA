"use client";

import { useEffect } from "react";

/**
 * PostHog instrumentation. No-op when NEXT_PUBLIC_POSTHOG_KEY is unset, so
 * the site works in dev / forks without analytics. When the key is present:
 *
 *   - tracks page views
 *   - exposes window.costdnaTrack(event, props) for AskLive to call when
 *     a question is submitted or an answer comes back
 *
 * Free-tier sign-up: posthog.com → create project → copy "Project API key"
 * → set NEXT_PUBLIC_POSTHOG_KEY in Vercel env vars + redeploy.
 */
export default function Analytics() {
  useEffect(() => {
    const key = process.env.NEXT_PUBLIC_POSTHOG_KEY;
    if (!key) return;

    let cancelled = false;
    (async () => {
      const { default: posthog } = await import("posthog-js");
      if (cancelled) return;
      posthog.init(key, {
        api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST || "https://us.i.posthog.com",
        capture_pageview: true,
        autocapture: true,
        persistence: "memory",   // no cookies — privacy-respecting default
      });
      // Expose a thin wrapper so AskLive can fire events without importing
      // posthog directly (keeps the heavy SDK out of the main client bundle).
      (window as unknown as { costdnaTrack?: (e: string, p?: object) => void })
        .costdnaTrack = (event, props) => posthog.capture(event, props);
    })();
    return () => { cancelled = true; };
  }, []);
  return null;
}
