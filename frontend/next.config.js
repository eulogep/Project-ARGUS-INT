// frontend/next.config.js
/** @type {import('next').NextConfig} */
const nextConfig = {
  // Production optimizations
  output: 'standalone',
  reactStrictMode: true,
  poweredByHeader: false,  // Security: Don't advertise Next.js
  compress: true,
  
  // Image optimization (disabled for standalone, use external CDN if needed)
  images: {
    unoptimized: true,
  },
  
  // Security headers (defense in depth, also set at reverse proxy level)
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-DNS-Prefetch-Control',
            value: 'on'
          },
          {
            key: 'Strict-Transport-Security',
            value: 'max-age=63072000; includeSubDomains; preload'
          },
          {
            key: 'X-Frame-Options',
            value: 'DENY'
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff'
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin'
          },
          {
            key: 'Permissions-Policy',
            value: 'camera=(), microphone=(), geolocation=(), interest-cohort=()'
          }
        ],
      },
    ]
  },
}

module.exports = nextConfig
