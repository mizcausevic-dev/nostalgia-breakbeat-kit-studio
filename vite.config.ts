import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const root = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  base: "./",
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": resolve(root, "src") } },
  server: { host: "127.0.0.1", port: 43129 },
  preview: { host: "127.0.0.1", port: 43129 },
  build: {
    rollupOptions: {
      input: {
        main: resolve(root, "index.html"),
        article: resolve(root, "article.html"),
      },
    },
  },
});
