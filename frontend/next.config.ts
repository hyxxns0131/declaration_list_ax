import type { NextConfig } from "next";

// 정적 export만 쓴다 (AGENTS 0-2). output: "export"를 지우면 버그다.
const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
};

export default nextConfig;
