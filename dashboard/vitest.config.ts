import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react-swc";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.{test,spec}.{ts,tsx}"],

    // 进程池配置 - 解决多进程 CPU 占用过高问题
    pool: "threads",
    poolOptions: {
      threads: {
        // 限制最大线程数 (默认是 CPU 核心数，可能过多)
        maxThreads: 4,
        // 最小线程数
        minThreads: 1,
        // 测试结束后自动终止线程
        isolate: true,
      },
    },

    // 单次运行模式下的优化
    // 如果不需要并行，可以设置 false 来减少资源占用
    // threads: false,  // 完全禁用多线程 (单进程运行)

    // 测试超时配置
    testTimeout: 10000,
    hookTimeout: 10000,

    // teardown 超时 - 确保测试结束后清理资源
    teardownTimeout: 5000,

    // watch 模式下隔离 - 避免进程残留
    isolate: true,

    // 失败时立即停止 (可选，减少资源占用)
    // bail: 1,
  },
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
});
