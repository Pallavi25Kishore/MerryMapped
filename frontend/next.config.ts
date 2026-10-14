import type { NextConfig } from "next";

// Where the FastAPI backend runs. The browser only ever talks to this website: requests to
// /api/... are passed through to the backend, so the backend needs no cross-site permissions.
const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  devIndicators: false, // the Next.js badge only shows while developing; errors still appear
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${BACKEND_URL}/api/:path*` }];
  },
  experimental: {
    proxyTimeout: 120_000, // planning takes up to about a minute; the default gives up after 30 s
  },
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
