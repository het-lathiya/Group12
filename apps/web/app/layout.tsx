import type { Metadata } from "next";
import { Inter } from "next/font/google";

import { Providers } from "@/components/shell/Providers";

import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "AI Travel Planner",
  description:
    "Describe a trip and get a day-by-day, costed itinerary you can edit. Plans are drafts with labelled estimates.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${inter.variable} h-full antialiased`}>
      <body className="min-h-full">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
