import React from "react";
import { cn } from "@/lib/utils";

interface SpinnerProps {
  size?: "xs" | "sm" | "md" | "lg" | "xl";
  className?: string;
  label?: string;
}

const sizeClasses = {
  xs: "h-3 w-3 border",
  sm: "h-4 w-4 border-2",
  md: "h-6 w-6 border-2",
  lg: "h-8 w-8 border-[3px]",
  xl: "h-12 w-12 border-4",
};

export function Spinner({ size = "md", className, label }: SpinnerProps) {
  return (
    <div
      role="status"
      aria-label={label || "Loading"}
      className={cn("inline-flex items-center justify-center", className)}
    >
      <div
        className={cn(
          "animate-spin rounded-full border-gray-200 border-t-brand-600",
          sizeClasses[size]
        )}
      />
      {label && <span className="sr-only">{label}</span>}
    </div>
  );
}

// Full-page loading state
export function PageLoader({ message = "Loading..." }: { message?: string }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-gray-50">
      <Spinner size="xl" />
      <p className="text-sm text-gray-500">{message}</p>
    </div>
  );
}
