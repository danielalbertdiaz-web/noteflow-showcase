"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Stethoscope, CheckCircle, Loader2 } from "lucide-react";
import { setTokens } from "@/lib/auth";

export default function CallbackPageWrapper() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <CallbackPage />
    </Suspense>
  );
}

function CallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [done, setDone] = useState(false);

  useEffect(() => {
    const accessToken = searchParams.get("access_token");
    const refreshToken = searchParams.get("refresh_token");

    if (accessToken && refreshToken) {
      setTokens({
        accessToken,
        refreshToken,
        tokenType: "bearer",
        expiresIn: 900,
      });
      setDone(true);
      setTimeout(() => router.replace("/dashboard"), 1000);
    }
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
        <div className="flex flex-col items-center gap-4 text-center">
          {done ? (
            <>
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
            </>
          ) : (
            <>
              <Loader2 className="h-10 w-10 text-brand-600 animate-spin" />
              <div>
                <h2 className="text-base font-semibold text-gray-900">
                  Signing you in...
                </h2>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
