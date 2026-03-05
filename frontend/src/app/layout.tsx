import type { Metadata } from "next";
import "./globals.css";
import AppSidebar from "@/components/AppSidebar";
import { ThemeProvider } from "@/components/ThemeProvider";

export const metadata: Metadata = {
  title: "Ani-Log — Autonomous Scene Contextualizer",
  description:
    "A searchable wiki that automatically catalogs every character, location, and item from your anime.",
};

// Inlined before first paint to prevent flash of wrong theme
const themeScript = `(function(){
  try {
    var t = localStorage.getItem('ani-log-theme');
    var isDark = t !== 'light';
    document.documentElement.classList.toggle('dark', isDark);
    document.documentElement.classList.toggle('light', !isDark);
  } catch(e) {
    document.documentElement.classList.add('dark');
  }
})();`;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="h-screen overflow-hidden bg-surface-950">
        <ThemeProvider>
          <div className="flex h-full w-full">
            <AppSidebar />
            <main className="flex-1 overflow-y-auto">{children}</main>
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}
