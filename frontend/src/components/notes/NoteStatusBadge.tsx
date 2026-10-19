import React from "react";
import {
  FileText,
  Loader2,
  Clock,
  CheckCircle,
  CheckCheck,
  XCircle,
  FileEdit,
  Layers,
} from "lucide-react";
import { Badge, statusToBadgeVariant } from "@/components/ui/Badge";
import { formatNoteStatus } from "@/lib/utils";
import type { NoteStatus } from "@/types";

interface NoteStatusBadgeProps {
  status: NoteStatus;
  showIcon?: boolean;
  size?: "sm" | "md";
}

const statusIcons: Record<NoteStatus, React.ComponentType<{ className?: string }>> = {
  draft: FileText,
  processing: Loader2,
  transcribed: FileEdit,
  structured: Layers,
  reviewed: Clock,
  approved: CheckCircle,
  submitted: CheckCheck,
  failed: XCircle,
};

export function NoteStatusBadge({
  status,
  showIcon = true,
  size = "md",
}: NoteStatusBadgeProps) {
  const variant = statusToBadgeVariant(status);
  const Icon = statusIcons[status];
  const label = formatNoteStatus(status);

  return (
    <Badge variant={variant} size={size} dot={!showIcon}>
      {showIcon && (
        <Icon
          className={`shrink-0 ${size === "sm" ? "h-3 w-3" : "h-3.5 w-3.5"} ${
            status === "processing" ? "animate-spin" : ""
          }`}
        />
      )}
      {label}
    </Badge>
  );
}
