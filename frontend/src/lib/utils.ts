// Utility for merging class names (lightweight clsx alternative)
export function cn(...classes: (string | undefined | null | false)[]): string {
  return classes.filter(Boolean).join(" ");
}

export function formatVisitType(type: string): string {
  const map: Record<string, string> = {
    initial_eval: "Initial Eval",
    follow_up: "Follow-up",
    re_eval: "Re-evaluation",
    discharge: "Discharge",
    recertification: "Recertification",
    progress_note: "Progress Note",
  };
  return map[type] ?? type;
}

export function formatNoteStatus(status: string): string {
  const map: Record<string, string> = {
    draft: "Draft",
    processing: "Processing",
    transcribed: "Transcribed",
    structured: "Structured",
    reviewed: "Ready for Review",
    approved: "Approved",
    submitted: "Submitted",
    failed: "Failed",
  };
  return map[status] ?? status;
}
