import React from "react";
import { cn } from "@/lib/utils";
import type { NoteStatus } from "@/types";

type BadgeVariant =
  | "default"
  | "primary"
  | "success"
  | "warning"
  | "danger"
  | "info"
  | "draft"
  | "processing"
  | "reviewed"
  | "approved"
  | "submitted"
  | "failed"
  | "transcribed"
  | "structured";

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  size?: "sm" | "md";
  dot?: boolean;
}

const variantClasses: Record<BadgeVariant, string> = {
  default: "bg-gray-100 text-gray-700",
  primary: "bg-brand-100 text-brand-700",
  success: "bg-green-100 text-green-700",
  warning: "bg-amber-100 text-amber-700",
  danger: "bg-red-100 text-red-700",
  info: "bg-blue-100 text-blue-700",
  // Note status specific
  draft: "bg-gray-100 text-gray-700",
  processing: "bg-blue-100 text-blue-700",
  transcribed: "bg-indigo-100 text-indigo-700",
  structured: "bg-purple-100 text-purple-700",
  reviewed: "bg-amber-100 text-amber-700",
  approved: "bg-green-100 text-green-700",
  submitted: "bg-teal-100 text-teal-700",
  failed: "bg-red-100 text-red-700",
};

const dotColors: Record<BadgeVariant, string> = {
  default: "bg-gray-400",
  primary: "bg-brand-500",
  success: "bg-green-500",
  warning: "bg-amber-500",
  danger: "bg-red-500",
  info: "bg-blue-500",
  draft: "bg-gray-400",
  processing: "bg-blue-500",
  transcribed: "bg-indigo-500",
  structured: "bg-purple-500",
  reviewed: "bg-amber-500",
  approved: "bg-green-500",
  submitted: "bg-teal-500",
  failed: "bg-red-500",
};

export function Badge({
  variant = "default",
  size = "md",
  dot = false,
  children,
  className,
  ...props
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full font-medium",
        size === "sm" ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-xs",
        variantClasses[variant],
        className
      )}
      {...props}
    >
      {dot && (
        <span
          className={cn(
            "h-1.5 w-1.5 rounded-full shrink-0",
            dotColors[variant]
          )}
        />
      )}
      {children}
    </span>
  );
}

// Convenience function to get badge variant from note status
export function statusToBadgeVariant(status: NoteStatus): BadgeVariant {
  const map: Record<NoteStatus, BadgeVariant> = {
    draft: "draft",
    processing: "processing",
    transcribed: "transcribed",
    structured: "structured",
    reviewed: "reviewed",
    approved: "approved",
    submitted: "submitted",
    failed: "failed",
  };
  return map[status] ?? "default";
}
