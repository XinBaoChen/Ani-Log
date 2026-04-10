/** @type {import('next').NextConfig} */
const internalApiBase =
  process.env.INTERNAL_API_URL ||
  (process.env.NODE_ENV === "production" ? "http://backend:8000" : "http://localhost:8000");

const nextConfig = {
  // Prevent Next.js from issuing 308 redirects on /api/* trailing slashes
  // (the backend defines some routes with trailing slashes like /api/sessions/)
  skipTrailingSlashRedirect: true,
  images: {
    remotePatterns: [
      {
        protocol: "http",
        hostname: "localhost",
        port: "8000",
      },
    ],
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${internalApiBase}/api/:path*`,
      },
      {
        source: "/data/:path*",
        destination: `${internalApiBase}/data/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
