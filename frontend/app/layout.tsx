import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";

const geist = localFont({
  src: "./fonts/Geist.woff2",
  variable: "--font-geist",
  weight: "100 900",
  display: "swap"
});
const mono = localFont({
  src: "./fonts/GeistMono.woff2",
  variable: "--font-geist-mono",
  weight: "100 900",
  display: "swap",
  adjustFontFallback: false
});

export const metadata: Metadata = {
  title: "DeHalu",
  description: "Agentic hallucination detection and mitigation for local CodeLLMs"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${geist.variable} ${mono.variable} antialiased`}>{children}</body>
    </html>
  );
}
