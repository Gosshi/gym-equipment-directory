import bundleAnalyzer from "@next/bundle-analyzer";

const withBundleAnalyzer = bundleAnalyzer({
  enabled: process.env.ANALYZE === "true",
  openAnalyzer: false,
  generateStatsFile: true,
});

const nextConfig = {
  reactStrictMode: true,
};

export default withBundleAnalyzer(nextConfig);
