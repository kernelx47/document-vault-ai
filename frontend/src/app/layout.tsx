import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "VaultMind — Your Documents, Decoded",
  description: "AI-powered document intelligence. Upload, search, and get instant answers from every page.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="overflow-hidden">{children}</body>
    </html>
  );
}
