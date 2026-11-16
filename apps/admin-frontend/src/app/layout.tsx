import type { Metadata } from "next";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "CampusAI Administration Portal | Institutional Knowledge Hub",
  description: "Secure, role-gated administrative portal for College and Global Super Admins.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-[#0B0B0D] text-[#F5F5F5] antialiased min-h-screen">
        {children}
      </body>
    </html>
  );
}
