/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  images: {
    contentSecurityPolicy: "default-src 'self'; script-src 'none'; sandbox;",
    minimumCacheTTL: 31536000, // 1 year — stock images don't change
  },
  async headers() {
    return [
      {
        // Static images served directly from /public
        source: "/images/:path*",
        headers: [
          {
            key: "Cache-Control",
            value: "public, max-age=31536000, immutable",
          },
        ],
      },
    ];
  },
}

module.exports = nextConfig