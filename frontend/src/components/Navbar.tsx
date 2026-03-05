"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Sparkles,
  Search,
  Users,
  Film,
  MonitorPlay,
  BookOpen,
  Sun,
  Moon,
} from "lucide-react";
import { useTheme } from "@/components/ThemeProvider";

const links = [
  { href: "/", label: "Home", icon: Sparkles },
  { href: "/search", label: "Search", icon: Search },
  { href: "/characters", label: "Characters", icon: Users },
  { href: "/sessions", label: "Sessions", icon: Film },
  { href: "/capture", label: "Capture", icon: MonitorPlay },
];

export default function Navbar() {
  const pathname = usePathname();
  const { theme, toggle } = useTheme();

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-surface-950/80 backdrop-blur-xl border-b border-surface-800/50">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-accent-pink flex items-center justify-center shadow-lg shadow-primary-500/20 group-hover:shadow-primary-500/40 transition-shadow">
            <BookOpen className="w-4 h-4 text-white" />
          </div>
          <span className="text-lg font-bold tracking-tight">
            <span className="text-gradient">Ani-Log</span>
          </span>
        </Link>

        <div className="flex items-center gap-1">
          {/* Navigation Links */}
          {links.map((link) => {
            const isActive =
              link.href === "/"
                ? pathname === "/"
                : pathname.startsWith(link.href);

            return (
              <Link
                key={link.href}
                href={link.href}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? "bg-primary-600/15 text-primary-400"
                    : "text-surface-400 hover:text-surface-200 hover:bg-surface-800/50"
                }`}
              >
                <link.icon className="w-4 h-4" />
                <span className="hidden sm:inline">{link.label}</span>
              </Link>
            );
          })}

          {/* Theme toggle */}
          <button
            onClick={toggle}
            aria-label="Toggle theme"
            className="ml-1 p-2 rounded-lg text-surface-400 hover:text-surface-200 hover:bg-surface-800/50 transition-all"
          >
            {theme === "dark" ? (
              <Sun className="w-4 h-4" />
            ) : (
              <Moon className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>
    </nav>
  );
}
