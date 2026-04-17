/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  // Note: API proxy with auth is handled by src/app/api/[...path]/route.ts
  // Do NOT add rewrites here as they bypass the route handler
};

module.exports = nextConfig;
