"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated } from "@/lib/auth";
import { PageLoader } from "@/components/ui/Spinner";

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    if (isAuthenticated()) {
      router.replace("/dashboard");
    } else {
      router.replace("/auth/login");
    }
  }, [router]);

  return <PageLoader message="Starting NoteFlow..." />;
}
