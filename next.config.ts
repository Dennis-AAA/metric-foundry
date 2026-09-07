import type { NextConfig } from "next";

const pages = process.env.GITHUB_PAGES === "1";
const basePath = process.env.PAGES_BASE_PATH || process.env.NEXT_PUBLIC_BASE_PATH || "";

const nextConfig: NextConfig = {
  output: pages ? "export" : undefined,
  images: { unoptimized: true },
  trailingSlash: pages,
};

if (basePath) {
  nextConfig.basePath = basePath;
}

export default nextConfig;
