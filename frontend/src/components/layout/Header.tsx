"use client";

import { LogOut, Stethoscope, Bell } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

interface HeaderProps {
  showUserInfo?: boolean;
  title?: string;
  backButton?: React.ReactNode;
}

export function Header({
  showUserInfo = true,
  title,
  backButton,
}: HeaderProps) {
  const { user, logout } = useAuth();

  const displayName =
    user?.clinician
      ? `${(user.clinician as { firstName?: string; lastName?: string }).firstName || ""} ${(user.clinician as { firstName?: string; lastName?: string }).lastName || ""}`.trim()
      : user?.email?.split("@")[0] ?? "Clinician";

  return (
    <header className="sticky top-0 z-30 border-b border-gray-200 bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/80">
      <div className="mx-auto flex h-14 max-w-2xl items-center justify-between px-4">
        {/* Left: back button or logo */}
        <div className="flex items-center gap-3 min-w-0">
          {backButton ? (
            backButton
          ) : (
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600">
                <Stethoscope className="h-4 w-4 text-white" />
              </div>
              <span className="font-bold text-gray-900 text-base">
                {title || "NoteFlow"}
              </span>
            </div>
          )}
          {title && backButton && (
            <span className="truncate font-semibold text-gray-900 text-sm">
              {title}
            </span>
          )}
        </div>

        {/* Right: user info + actions */}
        {showUserInfo && (
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="relative rounded-full p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition-colors"
              aria-label="Notifications"
            >
              <Bell className="h-5 w-5" />
            </button>

            <div className="flex items-center gap-2">
              <div className="hidden sm:block text-right">
                <p className="text-xs font-medium text-gray-900 leading-none">
                  {displayName}
                </p>
                <p className="text-xs text-gray-500 mt-0.5">{user?.email}</p>
              </div>
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-100 text-brand-700 text-sm font-semibold uppercase">
                {displayName.charAt(0)}
              </div>
            </div>

            <button
              type="button"
              onClick={logout}
              className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition-colors"
              aria-label="Logout"
              title="Logout"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
