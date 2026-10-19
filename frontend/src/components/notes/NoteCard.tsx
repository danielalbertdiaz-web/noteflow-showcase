import React from "react";
import Link from "next/link";
import { formatDistanceToNow, parseISO } from "date-fns";
import { User, Calendar, ChevronRight } from "lucide-react";
import { NoteStatusBadge } from "./NoteStatusBadge";
import { formatVisitType } from "@/lib/utils";
import type { Note } from "@/types";

interface NoteCardProps {
  note: Note;
  className?: string;
}

export function NoteCard({ note, className }: NoteCardProps) {
  const timeAgo = (() => {
    try {
      if (!note.createdAt) return 'recently';
      return formatDistanceToNow(parseISO(note.createdAt), { addSuffix: true });
    } catch {
      return 'recently';
    }
  })();

  const visitDate = (() => {
    try {
      if (!note.visitDate) return 'N/A';
      const d = parseISO(note.visitDate);
      return d.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      });
    } catch {
      return note.visitDate || 'N/A';
    }
  })();

  return (
    <Link
      href={`/notes/${note.id}`}
      className={`block bg-white hover:bg-gray-50 active:bg-gray-100 transition-colors ${className ?? ""}`}
    >
      <div className="flex items-start gap-3 px-4 py-3.5">
        {/* Avatar */}
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-brand-50 text-brand-600">
          <User className="h-5 w-5" />
        </div>

        {/* Content */}
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <p className="truncate font-medium text-gray-900 text-sm">
              {note.patientName || "Unknown Patient"}
            </p>
            <NoteStatusBadge status={note.status} size="sm" />
          </div>

          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <Calendar className="h-3 w-3 shrink-0" />
              {visitDate}
            </span>
            <span className="text-gray-300">·</span>
            <span>{formatVisitType(note.visitType)}</span>
            <span className="text-gray-300">·</span>
            <span>{timeAgo}</span>
          </div>

          {note.flags && Array.isArray(note.flags) && note.flags.length > 0 && (
            <p className="mt-1 truncate text-xs text-amber-600">
              ⚠ {note.flags[0]}
              {note.flags.length > 1 && ` +${note.flags.length - 1} more`}
            </p>
          )}
        </div>

        <ChevronRight className="h-4 w-4 shrink-0 text-gray-300 mt-1" />
      </div>
    </Link>
  );
}
