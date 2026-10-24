import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  async redirects() {
    return [
      {
        source: "/dashboard/:path*",
        destination: "/",
        permanent: false,
      },
      {
        source: "/dashboard",
        destination: "/",
        permanent: false,
      },
      {
        source: "/playground",
        destination: "/",
        permanent: false,
      },
      {
        source: "/mcp",
        destination: "/",
        permanent: false,
      },
      {
        source: "/integrations/:path*",
        destination: "/",
        permanent: false,
      },
      {
        source: "/agent-runs/:path*",
        destination: "/",
        permanent: false,
      },
      {
        source: "/activity",
        destination: "/",
        permanent: false,
      },
      {
        source: "/settings",
        destination: "/",
        permanent: false,
      },
      {
        source: "/create",
        destination: "/",
        permanent: false,
      },
    ];
  },
};

export default nextConfig;
