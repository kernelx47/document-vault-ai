import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Document Vault AI",
  description: "Upload documents and chat with them using AI",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
