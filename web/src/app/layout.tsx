import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AgentIQ | Document intelligence",
  description: "A retrieval-led research desk for your documents.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
