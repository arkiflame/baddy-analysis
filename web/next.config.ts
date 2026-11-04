import type { NextConfig } from "next";

// Static export: `next build` writes a plain HTML/CSS/JS site to web/out that any static host
// (Vercel included) can serve. Every page is rendered at build time from web/public/data/*.json,
// which scripts/export_web.py produces; the site never computes a number itself.
const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
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
