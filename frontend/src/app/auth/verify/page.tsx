"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Stethoscope, CheckCircle, XCircle, Loader2 } from "lucide-react";
import { authApi } from "@/lib/api";
import { setTokens } from "@/lib/auth";

type VerifyState = "loading" | "success" | "error";

export default function VerifyPageWrapper() {
  return <Suspense fallback={<div>Loading...</div>}><VerifyPage /></Suspense>;
}

function VerifyPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [state, setState] = useState<VerifyState>("loading");
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    const token = searchParams.get("token");

    if (!token) {
      setState("error");
      setErrorMessage("No verification token found in the link.");
      return;
    }

    let cancelled = false;

    authApi
      .verifyMagicLink(token)
      .then((tokens) => {
        if (cancelled) return;
        setTokens(tokens);
        setState("success");
        // Brief delay so user sees success state
        setTimeout(() => {
          if (!cancelled) router.replace("/dashboard");
        }, 1500);
      })
      .catch((err) => {
        if (cancelled) return;
        setState("error");
        const msg =
          err?.response?.data?.detail ||
          err?.message ||
          "The link may have expired or already been used.";
        setErrorMessage(msg);
      });

    return () => {
      cancelled = true;
    };
  }, [searchParams, router]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-b from-brand-50 to-white px-4">
      <div className="mb-8 flex flex-col items-center gap-3">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-600 shadow-lg shadow-brand-200">
          <Stethoscope className="h-7 w-7 text-white" />
        </div>
        <h1 className="text-xl font-bold text-gray-900">NoteFlow</h1>
      </div>

      <div className="w-full max-w-sm rounded-2xl bg-white border border-gray-200 shadow-xl p-8">
        {state === "loading" && (
          <div className="flex flex-col items-center gap-4 text-center">
            <Loader2 className="h-10 w-10 text-brand-600 animate-spin" />
            <div>
              <h2 className="text-base font-semibold text-gray-900">
                Verifying your link...
              </h2>
              <p className="mt-1 text-sm text-gray-500">Just a moment</p>
            </div>
          </div>
        )}

        {state === "success" && (
          <div className="flex flex-col items-center gap-4 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-green-100">
              <CheckCircle className="h-7 w-7 text-green-600" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-gray-900">
                Signed in successfully!
              </h2>
              <p className="mt-1 text-sm text-gray-500">
                Redirecting to your dashboard...
              </p>
            </div>
          </div>
        )}

        {state === "error" && (
          <div className="flex flex-col items-center gap-4 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-red-100">
              <XCircle className="h-7 w-7 text-red-600" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-gray-900">
                Verification failed
              </h2>
              <p className="mt-1.5 text-sm text-gray-600">{errorMessage}</p>
            </div>
            <Link
              href="/auth/login"
              className="mt-2 inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-brand-700 transition-colors"
            >
              Back to Login
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
