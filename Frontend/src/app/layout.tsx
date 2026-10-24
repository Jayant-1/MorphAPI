import type { Metadata } from "next";
import { Syne, IBM_Plex_Mono } from "next/font/google";
import "@fontsource/uncut-sans/400.css";
import "@fontsource/uncut-sans/500.css";
import "./globals.css";

const syne = Syne({
  subsets: ["latin"],
  weight: ["600", "700"],
  variable: "--font-syne",
  display: "swap",
});

const ibmPlexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "MorphAPI",
  description:
    "Autonomous Web-to-API and Model Context Protocol (MCP) gateway with self-healing selector synthesis and real-time execution telemetry.",
  icons: {
    icon: "/logo.png",
    shortcut: "/logo.png",
    apple: "/logo.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`dark ${syne.variable} ${ibmPlexMono.variable}`}>
      <body className="antialiased selection:bg-[#C3D1B8] selection:text-[#17201C] font-sans bg-[#10171B] text-[#EDF1EE] min-h-screen">
        {children}
      </body>
    </html>
  );
}
