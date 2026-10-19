"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, PlusCircle, Settings } from "lucide-react";
import { cn } from "@/lib/utils";

interface NavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  exact?: boolean;
}

const navItems: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: Home, exact: true },
  { href: "/notes/new", label: "New Note", icon: PlusCircle },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function BottomNav() {
  const pathname = usePathname();

  const isActive = (item: NavItem) => {
    if (item.exact) return pathname === item.href;
    return pathname.startsWith(item.href);
  };

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-40 border-t border-gray-200 bg-white safe-area-pb"
      aria-label="Main navigation"
    >
      <div className="mx-auto flex max-w-lg items-center justify-around">
        {navItems.map((item) => {
          const active = isActive(item);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex flex-1 flex-col items-center gap-1 py-3 px-2 text-xs font-medium transition-colors",
                active
                  ? "text-brand-600"
                  : "text-gray-500 hover:text-gray-700"
              )}
              aria-current={active ? "page" : undefined}
            >
              <Icon
                className={cn(
                  "h-6 w-6 transition-transform",
                  active && "scale-110"
                )}
              />
              <span>{item.label}</span>
              {active && (
                <span className="absolute bottom-0 h-0.5 w-8 rounded-full bg-brand-600" />
              )}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
