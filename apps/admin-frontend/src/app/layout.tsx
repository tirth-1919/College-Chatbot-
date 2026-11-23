import type { Metadata } from "next";
import "@/styles/globals.css";
import { ThemeProvider } from "@/context/ThemeContext";

export const metadata: Metadata = {
  title: "AI FAQ Colleges Chatbot Administration Portal | Institutional Knowledge Hub",
  description: "Secure, role-gated administrative portal for College and Global Super Admins.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                try {
                  var saved = localStorage.getItem('campusai_theme');
                  var theme = (saved === 'light' || saved === 'dark') ? saved : 'dark';
                  if (theme === 'dark') {
                    document.documentElement.classList.add('dark');
                    document.documentElement.classList.remove('light');
                  } else {
                    document.documentElement.classList.add('light');
                    document.documentElement.classList.remove('dark');
                  }
                  document.documentElement.style.colorScheme = theme;
                } catch (e) {}
              })();
            `,
          }}
        />
      </head>
      <body className="bg-background text-primaryText antialiased min-h-screen transition-colors duration-150">
        <ThemeProvider>
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
