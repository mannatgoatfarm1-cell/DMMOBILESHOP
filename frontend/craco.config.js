const path = require("path");

module.exports = {
  webpack: {
    alias: { "@": path.resolve(__dirname, "src") },
    configure: (config) => {
      config.watchOptions = { ...config.watchOptions, ignored: ["**/node_modules/**", "**/.git/**", "**/build/**", "**/dist/**"] };
      return config;
    },
  },
};