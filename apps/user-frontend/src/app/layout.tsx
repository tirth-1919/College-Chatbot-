import type { Metadata } from "next";
import "@/styles/globals.css";
import { Navbar } from "@/components/Navbar";

export const metadata: Metadata = {
  title: "AI FAQ College Chat Bot | Verified College Intelligence",
  description: "Accurate, source-grounded college information powered by official websites, brochures, and AI.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-[#0B0B0D] text-[#F5F5F5] antialiased">
        <Navbar />
        <main>{children}</main>
      </body>
    </html>
  );
}

