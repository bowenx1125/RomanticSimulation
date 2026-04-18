import "./globals.css";
import type { Metadata } from "next";
import { ReactNode } from "react";

export const metadata: Metadata = {
  title: "恋爱模拟器 Phase 3",
  description: "多角色平权、pairwise relationship graph、多轮多人 runtime 的关系模拟器。",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
