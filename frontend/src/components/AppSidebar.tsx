"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import clsx from "clsx";
import { BrandLogo, BrandWordmark } from "@/components/BrandLogo";

function IconSidebar() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <path d="M9 3v18" />
    </svg>
  );
}

const navItems = [
  {
    href: "/",
    label: "Chat",
    icon: (
      <svg className="h-[18px] w-[18px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
      </svg>
    ),
  },
  {
    href: "/upload",
    label: "Doc Uploader",
    icon: (
      <svg className="h-[18px] w-[18px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
        <polyline points="17 8 12 3 7 8" />
        <line x1="12" y1="3" x2="12" y2="15" />
      </svg>
    ),
  },
  {
    href: "/activity",
    label: "Activity Monitor",
    icon: (
      <svg className="h-[18px] w-[18px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
      </svg>
    ),
  },
  {
    href: "/platform",
    label: "Insights Dashboard",
    icon: (
      <svg className="h-[18px] w-[18px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 3v18h18" />
        <path d="M7 14l4-4 4 4 5-6" />
      </svg>
    ),
  },
];

interface AppSidebarProps {
  children: React.ReactNode;
}

export default function AppSidebar({ children }: AppSidebarProps) {
  const pathname = usePathname();
  const [open, setOpen] = useState(true);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[var(--iris-haze)]">
      {/* Sidebar */}
      <aside
        className={clsx(
          "flex flex-col border-r border-[var(--lavender-mist)] bg-[var(--pure-paper)] transition-all duration-200 ease-in-out overflow-hidden",
          open ? "w-[260px]" : "w-0",
        )}
      >
        <div className="flex min-w-[260px] flex-col h-full">
          {/* Brand + toggle */}
          <div className="flex items-center justify-between px-3 py-3">
            <Link href="/" className="flex items-center gap-2 px-1.5">
              <BrandLogo size={22} />
              <BrandWordmark />
            </Link>
            <button
              onClick={() => setOpen(false)}
              className="rounded-[var(--radius)] p-1.5 text-[var(--heather)] hover:bg-[var(--iris-haze)]"
              title="Close sidebar"
            >
              <IconSidebar />
            </button>
          </div>

          {/* Nav links */}
          <nav className="flex-1 overflow-y-auto px-2 py-2">
            <div className="space-y-0.5">
              {navItems.map((item) => {
                const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={clsx(
                      "flex w-full items-center gap-2.5 rounded-[var(--radius)] px-3 py-2.5 text-[14px] transition-colors",
                      active
                        ? "bg-[var(--iris-haze)] font-medium text-[var(--deep-ink)]"
                        : "text-[var(--heather)] hover:bg-[var(--iris-haze)] hover:text-[var(--deep-ink)]",
                    )}
                  >
                    {item.icon}
                    <span className="flex-1 text-left">{item.label}</span>
                    {active && (
                      <span className="h-1.5 w-1.5 rounded-full bg-[var(--electric-violet)]" />
                    )}
                  </Link>
                );
              })}
            </div>
          </nav>

          {/* Footer */}
          <div className="border-t border-[var(--lavender-mist)] px-4 py-3">
            <p className="text-[11px] text-[var(--mist)]">VaultMind v1.0</p>
          </div>
        </div>
      </aside>

      {/* Main area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Collapsed sidebar toggle */}
        {!open && (
          <button
            onClick={() => setOpen(true)}
            className="absolute left-2 top-3 z-30 rounded-[var(--radius)] p-1.5 text-[var(--heather)] hover:bg-[var(--lavender-mist)]"
            title="Open sidebar"
          >
            <IconSidebar />
          </button>
        )}
        {children}
      </div>
    </div>
  );
}
