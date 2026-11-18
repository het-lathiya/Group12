import type { NextConfig } from "next";

// Staging API. The browser always calls same-origin /api/v1, so the API's CORS list is untouched:
// `next dev` proxies it with the rewrite below; on AWS, CloudFront routes /api/* to this origin.
const API_ORIGIN = process.env.API_ORIGIN ?? "https://gr-8c92985228bc4ea8ada4840e8cf45d50.ecs.ap-south-1.on.aws";
const isStatic = process.env.STATIC_EXPORT === "1";

const nextConfig: NextConfig = isStatic
  ? { output: "export", trailingSlash: true, images: { unoptimized: true } }
  : {
      trailingSlash: true,
      images: { unoptimized: true },
      skipTrailingSlashRedirect: true,
      async rewrites() {
        return [{ source: "/api/:path*", destination: `${API_ORIGIN}/api/:path*` }];
      },
    };

export default nextConfig;
