import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TuneMorph — Audio into new arrangements",
  description:
    "Transform audio you own into coherent, style-aware MIDI arrangements.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
