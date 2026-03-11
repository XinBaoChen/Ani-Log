/** @type {import('next').NextConfig} */
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
        destination: "http://localhost:8000/api/:path*",
      },
    ];
  },
};

module.exports = nextConfig;
