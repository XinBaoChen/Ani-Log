"use client";

import React, { useState } from "react";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import {
  Sparkles,
  Search,
  Users,
  Film,
  MonitorPlay,
  BookOpen,
  Sun,
  Moon,
  Clapperboard,
} from "lucide-react";
import Link from "next/link";
import { Sidebar, SidebarBody, SidebarLink } from "@/components/ui/sidebar";
import { useTheme } from "@/components/ThemeProvider";
import { cn } from "@/lib/utils";

const navLinks = [
  { href: "/", label: "Home", icon: <Sparkles className="w-5 h-5 flex-shrink-0" /> },
  { href: "/search", label: "Search", icon: <Search className="w-5 h-5 flex-shrink-0" /> },
  { href: "/characters", label: "Characters", icon: <Users className="w-5 h-5 flex-shrink-0" /> },
  { href: "/scenes", label: "Scenes", icon: <Clapperboard className="w-5 h-5 flex-shrink-0" /> },
  { href: "/sessions", label: "Sessions", icon: <Film className="w-5 h-5 flex-shrink-0" /> },
  { href: "/capture", label: "Capture", icon: <MonitorPlay className="w-5 h-5 flex-shrink-0" /> },
];

const AniLogLogo = () => {
  return (
    <Link href="/" className="flex items-center gap-2.5 py-1 group">
      <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-accent-pink flex items-center justify-center flex-shrink-0 shadow-lg shadow-primary-500/25 group-hover:shadow-primary-500/40 transition-shadow">
        <BookOpen className="w-4 h-4 text-white" />
      </div>
      <motion.span
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="text-base font-bold tracking-tight whitespace-pre"
      >
        <span className="text-gradient">Ani-Log</span>
      </motion.span>
    </Link>
  );
};

const AniLogLogoIcon = () => {
  return (
    <Link href="/" className="flex items-center py-1">
      <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-accent-pink flex items-center justify-center flex-shrink-0">
        <BookOpen className="w-4 h-4 text-white" />
      </div>
    </Link>
  );
};

export default function AppSidebar() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  const { theme, toggle } = useTheme();

  const themeLink = {
    label: theme === "dark" ? "Light mode" : "Dark mode",
    href: "#",
    icon:
      theme === "dark" ? (
        <Sun className="w-5 h-5 flex-shrink-0 text-surface-400" />
      ) : (
        <Moon className="w-5 h-5 flex-shrink-0 text-surface-400" />
      ),
  };

  return (
    <Sidebar open={open} setOpen={setOpen}>
      <SidebarBody className="justify-between gap-8 h-full">
        {/* Top section */}
        <div className="flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
          {open ? <AniLogLogo /> : <AniLogLogoIcon />}

          <div className="mt-8 flex flex-col gap-1">
            {navLinks.map((link) => {
              const isActive =
                link.href === "/"
                  ? pathname === "/"
                  : pathname.startsWith(link.href);
              return (
                <SidebarLink
                  key={link.href}
                  link={link}
                  active={isActive}
                />
              );
            })}
          </div>
        </div>

        {/* Bottom section */}
        <div>
          <div
            onClick={toggle}
            className={cn(
              "flex items-center justify-start gap-3 py-2 px-2 rounded-lg cursor-pointer transition-colors duration-150",
              "text-surface-400 hover:text-surface-200 hover:bg-surface-800/60"
            )}
          >
            <span className="flex-shrink-0">
              {theme === "dark" ? (
                <Sun className="w-5 h-5" />
              ) : (
                <Moon className="w-5 h-5" />
              )}
            </span>
            <motion.span
              animate={{
                display: open ? "inline-block" : "none",
                opacity: open ? 1 : 0,
              }}
              className="text-sm font-medium whitespace-pre"
            >
              {theme === "dark" ? "Light mode" : "Dark mode"}
            </motion.span>
          </div>
        </div>
      </SidebarBody>
    </Sidebar>
  );
}
