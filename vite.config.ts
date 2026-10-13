import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({ plugins: [react()], server: { proxy: { "/mcp": "http://localhost:8001", "/operator": "http://localhost:8001" } } });
