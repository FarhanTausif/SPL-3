import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DeHalu",
  description: "Agentic hallucination detection and mitigation for local CodeLLMs"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
