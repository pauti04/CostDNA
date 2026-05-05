/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    outputFileTracingIncludes: {
      "/api/ask": ["./public/data/scan.json"],
    },
  },
};

export default nextConfig;
