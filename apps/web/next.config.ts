import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // `standalone` emits a self-contained server bundle with only the node_modules
  // it actually reached, so the container image does not ship the whole
  // dependency tree. Vercel ignores this and builds its own way, so setting it
  // costs nothing there.
  output: "standalone",
};

export default nextConfig;
