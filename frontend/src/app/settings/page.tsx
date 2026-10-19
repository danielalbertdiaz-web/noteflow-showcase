"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { LogOut, User, Bell, Shield, HelpCircle, KeyRound, Eye, EyeOff, CheckCircle as CheckIcon, Loader2 } from "lucide-react";
import { Header } from "@/components/layout/Header";
import { BottomNav } from "@/components/layout/BottomNav";
import { useAuth } from "@/hooks/useAuth";
import { isAuthenticated } from "@/lib/auth";
import { usersApi } from "@/lib/api";

interface SettingRow {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  description?: string;
  action?: () => void;
  href?: string;
  danger?: boolean;
}

export default function SettingsPage() {
  const router = useRouter();
  const { user, logout } = useAuth();

  const [kinnserUsername, setKinnserUsername] = useState("");
  const [kinnserPassword, setKinnserPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [credsSaving, setCredsSaving] = useState(false);
  const [credsSaved, setCredsSaved] = useState(false);
  const [credsError, setCredsError] = useState<string | null>(null);
  const [credsLoaded, setCredsLoaded] = useState(false);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/auth/login");
    }
  }, [router]);

  useEffect(() => {
    async function loadCreds() {
      try {
        const creds = await usersApi.getKinnserCredentials();
        if (creds.kinnser_username) {
          setKinnserUsername(creds.kinnser_username);
        }
        setCredsLoaded(true);
      } catch {
        setCredsLoaded(true);
      }
    }
    if (isAuthenticated()) loadCreds();
  }, []);

  const handleSaveCredentials = async () => {
    if (!kinnserUsername || !kinnserPassword) {
      setCredsError("Both username and password are required");
      return;
    }
    setCredsSaving(true);
    setCredsError(null);
    setCredsSaved(false);
    try {
      await usersApi.updateKinnserCredentials(kinnserUsername, kinnserPassword);
      setCredsSaved(true);
      setKinnserPassword("");
      setTimeout(() => setCredsSaved(false), 3000);
    } catch (err) {
      setCredsError(err instanceof Error ? err.message : "Failed to save credentials");
    } finally {
      setCredsSaving(false);
    }
  };

  const displayName =
    user?.clinician
      ? `${(user.clinician as { firstName?: string }).firstName || ""} ${(user.clinician as { lastName?: string }).lastName || ""}`.trim()
      : user?.email?.split("@")[0] ?? "Clinician";

  const rows: SettingRow[] = [
    {
      icon: User,
      label: "Profile",
      description: "View and edit your clinician profile",
    },
    {
      icon: Bell,
      label: "Notifications",
      description: "Manage push notification preferences",
    },
    {
      icon: Shield,
      label: "Privacy & Security",
      description: "HIPAA settings, data retention",
    },
    {
      icon: HelpCircle,
      label: "Help & Support",
      description: "Documentation, contact support",
    },
    {
      icon: LogOut,
      label: "Sign Out",
      description: "Sign out of NoteFlow",
      action: logout,
      danger: true,
    },
  ];

  return (
    <div className="flex min-h-screen flex-col bg-gray-50">
      <Header showUserInfo={false} title="Settings" />

      <main className="flex-1">
        <div className="page-container">
          {/* User info card */}
          <div className="mb-6 rounded-xl bg-white border border-gray-200 shadow-sm px-4 py-4">
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-100 text-brand-700 text-lg font-bold uppercase">
                {displayName.charAt(0)}
              </div>
              <div>
                <p className="font-semibold text-gray-900">{displayName}</p>
                <p className="text-sm text-gray-500">{user?.email}</p>
                {user?.role && (
                  <p className="text-xs text-brand-600 capitalize mt-0.5">
                    {user.role}
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* WellSky Credentials */}
          <div className="mb-6 rounded-xl bg-white border border-gray-200 shadow-sm px-4 py-4">
            <div className="flex items-center gap-2 mb-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-50">
                <KeyRound className="h-4 w-4 text-blue-600" />
              </div>
              <div>
                <p className="font-semibold text-gray-900 text-sm">WellSky / Kinnser Credentials</p>
                <p className="text-xs text-gray-500">Used for automatic note submission</p>
              </div>
            </div>

            <div className="space-y-3">
              <div>
                <label htmlFor="kinnser-user" className="block text-xs font-medium text-gray-600 mb-1">
                  Username
                </label>
                <input
                  id="kinnser-user"
                  type="text"
                  value={kinnserUsername}
                  onChange={(e) => setKinnserUsername(e.target.value)}
                  placeholder="Enter WellSky username"
                  className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  autoComplete="username"
                />
              </div>

              <div>
                <label htmlFor="kinnser-pass" className="block text-xs font-medium text-gray-600 mb-1">
                  Password
                </label>
                <div className="relative">
                  <input
                    id="kinnser-pass"
                    type={showPassword ? "text" : "password"}
                    value={kinnserPassword}
                    onChange={(e) => setKinnserPassword(e.target.value)}
                    placeholder="Enter WellSky password"
                    className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 pr-10 text-sm text-gray-900 placeholder:text-gray-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                    autoComplete="current-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              {credsError && (
                <p className="text-xs text-red-600">{credsError}</p>
              )}

              {credsSaved && (
                <div className="flex items-center gap-1.5 text-xs text-green-600">
                  <CheckIcon className="h-3.5 w-3.5" />
                  Credentials saved securely
                </div>
              )}

              <button
                type="button"
                onClick={handleSaveCredentials}
                disabled={credsSaving}
                className="w-full rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
              >
                {credsSaving ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  "Save Credentials"
                )}
              </button>
            </div>
          </div>

          {/* Settings list */}
          <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden divide-y divide-gray-100">
            {rows.map((row) => {
              const Icon = row.icon;
              const content = (
                <div className="flex items-center gap-3 px-4 py-4 hover:bg-gray-50 active:bg-gray-100 transition-colors w-full text-left">
                  <div
                    className={`flex h-9 w-9 items-center justify-center rounded-lg ${
                      row.danger ? "bg-red-50" : "bg-gray-100"
                    }`}
                  >
                    <Icon
                      className={`h-4 w-4 ${
                        row.danger ? "text-red-500" : "text-gray-600"
                      }`}
                    />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p
                      className={`text-sm font-medium ${
                        row.danger ? "text-red-600" : "text-gray-900"
                      }`}
                    >
                      {row.label}
                    </p>
                    {row.description && (
                      <p className="text-xs text-gray-500 mt-0.5">
                        {row.description}
                      </p>
                    )}
                  </div>
                  {!row.danger && (
                    <svg
                      className="h-4 w-4 text-gray-300 shrink-0"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                    >
                      <path
                        fillRule="evenodd"
                        d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
                        clipRule="evenodd"
                      />
                    </svg>
                  )}
                </div>
              );

              if (row.action) {
                return (
                  <button
                    key={row.label}
                    type="button"
                    onClick={row.action}
                    className="w-full"
                  >
                    {content}
                  </button>
                );
              }

              return (
                <button key={row.label} type="button" className="w-full">
                  {content}
                </button>
              );
            })}
          </div>

          <p className="mt-6 text-center text-xs text-gray-400">
            NoteFlow v0.1.0 · HIPAA Compliant
          </p>
        </div>
      </main>

      <BottomNav />
    </div>
  );
}
