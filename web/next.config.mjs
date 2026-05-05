/** @type {import('next').NextConfig} */
const nextConfig = {
  outputFileTracingIncludes: {
    "/api/ask": ["./public/data/scan.json"],
  },
};

export default nextConfig;
