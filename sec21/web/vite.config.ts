import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// /api 요청은 20·21편 백엔드(8790)로 넘긴다 → 브라우저 입장에선 같은 주소라 CORS 설정이 필요 없다
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://127.0.0.1:8790" } },
});
