"use client";

import { useState } from "react";
import { Stethoscope, Mail, ArrowRight, CheckCircle } from "lucide-react";
import { authApi } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

type PageState = "idle" | "loading" | "success" | "error";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [state, setState] = useState<PageState>("idle");
  const [errorMessage, setErrorMessage] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;

    setState("loading");
    setErrorMessage("");

    try {
      await authApi.sendMagicLink(email.trim().toLowerCase());
      setState("success");
    } catch (err) {
      setState("error");
      const message =
        err instanceof Error
          ? err.message
          : "Failed to send magic link. Please try again.";
      setErrorMessage(message);
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-gradient-to-b from-brand-50 to-white">
      {/* Top decoration */}
      <div className="absolute inset-x-0 top-0 h-72 bg-gradient-to-b from-brand-600/10 to-transparent pointer-events-none" />

      <div className="relative flex flex-1 flex-col items-center justify-center px-4 py-12">
        {/* Logo */}
        <div className="mb-8 flex flex-col items-center gap-3 animate-fade-in">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-600 shadow-lg shadow-brand-200">
            <Stethoscope className="h-8 w-8 text-white" />
          </div>
          <div className="text-center">
            <h1 className="text-2xl font-bold text-gray-900">NoteFlow</h1>
            <p className="mt-1 text-sm text-gray-500">
              PT Clinical Documentation
            </p>
          </div>
        </div>

        {/* Card */}
        <div className="w-full max-w-sm rounded-2xl bg-white border border-gray-200 shadow-xl p-6 animate-fade-in">
          {state === "success" ? (
            /* Success state */
            <div className="flex flex-col items-center gap-4 py-4 text-center">
              <div className="flex h-14 w-14 items-center justify-center rounded-full bg-green-100">
                <CheckCircle className="h-7 w-7 text-green-600" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900">
                  Check your email!
                </h2>
                <p className="mt-1.5 text-sm text-gray-600">
                  We sent a magic link to{" "}
                  <span className="font-medium text-gray-900">{email}</span>.
                  Click the link to sign in.
                </p>
              </div>
              <p className="text-xs text-gray-400 mt-2">
                Didn&apos;t receive it?{" "}
                <button
                  type="button"
                  onClick={() => {
                    setState("idle");
                    setEmail("");
                  }}
                  className="text-brand-600 hover:text-brand-700 font-medium underline"
                >
                  Try again
                </button>
              </p>
            </div>
          ) : (
            /* Login form */
            <>
              <div className="mb-6">
                <h2 className="text-lg font-semibold text-gray-900">
                  Sign in to NoteFlow
                </h2>
                <p className="mt-1 text-sm text-gray-500">
                  Enter your email to receive a secure login link
                </p>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <Input
                  label="Email address"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  required
                  autoComplete="email"
                  autoFocus
                  leftElement={<Mail className="h-4 w-4" />}
                  error={
                    state === "error" ? errorMessage : undefined
                  }
                />

                <Button
                  type="submit"
                  variant="primary"
                  size="lg"
                  fullWidth
                  loading={state === "loading"}
                  rightIcon={<ArrowRight className="h-4 w-4" />}
                >
                  Send Magic Link
                </Button>
              </form>

              <p className="mt-5 text-center text-xs text-gray-400">
                By signing in, you agree to our{" "}
                <a href="#" className="text-brand-600 hover:underline">
                  Terms of Service
                </a>{" "}
                and{" "}
                <a href="#" className="text-brand-600 hover:underline">
                  Privacy Policy
                </a>
              </p>
            </>
          )}
        </div>

        {/* Footer */}
        <p className="mt-8 text-xs text-gray-400 text-center">
          HIPAA-compliant documentation platform
          <br />
          &copy; {new Date().getFullYear()} NoteFlow
        </p>
      </div>
    </div>
  );
}
