"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Save,
  CheckCircle,
  AlertTriangle,
  Send,
  RefreshCw,
  Loader2,
  User,
  Calendar,
  Clock,
  Upload,
} from "lucide-react";
import { notesApi } from "@/lib/api";
import { SOAPNoteEditor } from "@/components/notes/SOAPNoteEditor";
import { NoteStatusBadge } from "@/components/notes/NoteStatusBadge";
import { Button } from "@/components/ui/Button";
import { Spinner, PageLoader } from "@/components/ui/Spinner";
import { BottomNav } from "@/components/layout/BottomNav";
import { isAuthenticated } from "@/lib/auth";
import { formatVisitType } from "@/lib/utils";
import { parseISO, formatDistanceToNow } from "date-fns";
import type { Note, SOAPNote, NoteStatus } from "@/types";

const SUBMITTABLE_STATUSES: NoteStatus[] = [
  "reviewed",
  "approved",
  "draft",
  "structured",
];

export default function NoteDetailPage() {
  const params = useParams();
  const router = useRouter();
  const noteId = params.id as string;

  const [note, setNote] = useState<Note | null>(null);
  const [soapNote, setSoapNote] = useState<SOAPNote>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [approving, setApproving] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [pollingActive, setPollingActive] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Auth guard
  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/auth/login");
    }
  }, [router]);

  const loadNote = useCallback(async () => {
    try {
      const data = await notesApi.getNote(noteId);
      setNote(data);
      setSoapNote(data.structuredNote || {});
      setError(null);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load note"
      );
    } finally {
      setLoading(false);
    }
  }, [noteId]);

  useEffect(() => {
    loadNote();
  }, [loadNote]);

  // Poll for status updates when note is processing
  useEffect(() => {
    if (!note) return;

    const shouldPoll =
      note.status === "processing" || note.status === "transcribed";

    if (shouldPoll && !pollingActive) {
      setPollingActive(true);
      pollingRef.current = setInterval(async () => {
        try {
          const status = await notesApi.getNoteStatus(noteId);
          if (
            status.status !== "processing" &&
            status.status !== "transcribed"
          ) {
            // Reload full note when processing completes
            await loadNote();
            if (pollingRef.current) clearInterval(pollingRef.current);
            setPollingActive(false);
          }
        } catch {
          // Keep polling on error
        }
      }, 5000);
    }

    if (!shouldPoll && pollingRef.current) {
      clearInterval(pollingRef.current);
      setPollingActive(false);
    }

    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [note, noteId, pollingActive, loadNote]);

  const handleSave = async () => {
    if (!note) return;
    setSaving(true);
    setSaveSuccess(false);
    setSubmitError(null);

    try {
      const updated = await notesApi.updateSOAPNote(noteId, soapNote);
      setNote(updated);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      setSubmitError(
        err instanceof Error ? err.message : "Failed to save changes"
      );
    } finally {
      setSaving(false);
    }
  };

  const handleSubmitToWellSky = async () => {
    if (!note) return;
    setSubmitting(true);
    setSubmitError(null);

    try {
      const updated = await notesApi.submitToKinnser(noteId);
      setNote(updated);
    } catch (err) {
      setSubmitError(
        err instanceof Error
          ? err.message
          : "Failed to submit to WellSky"
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleApproveAndSubmit = async () => {
    if (!note) return;
    setApproving(true);
    setSubmitError(null);

    try {
      const updated = await notesApi.approveNote(noteId);
      setNote(updated);
    } catch (err) {
      setSubmitError(
        err instanceof Error
          ? err.message
          : "Failed to approve and submit to Kinnser"
      );
    } finally {
      setApproving(false);
    }
  };

  const canSubmit =
    note && SUBMITTABLE_STATUSES.includes(note.status);

  const isProcessing =
    note?.status === "processing" || note?.status === "transcribed";

  if (loading) return <PageLoader message="Loading note..." />;

  if (error && !note) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center px-4">
        <AlertTriangle className="h-10 w-10 text-red-400 mb-4" />
        <p className="text-base font-semibold text-gray-900">
          Failed to load note
        </p>
        <p className="mt-1 text-sm text-gray-500">{error}</p>
        <Link
          href="/dashboard"
          className="mt-4 text-sm text-brand-600 hover:text-brand-700 font-medium"
        >
          Back to Dashboard
        </Link>
      </div>
    );
  }

  const visitDateFormatted = (() => {
    try {
      return parseISO(note!.visitDate).toLocaleDateString("en-US", {
        weekday: "short",
        month: "short",
        day: "numeric",
        year: "numeric",
      });
    } catch {
      return note!.visitDate;
    }
  })();

  const timeAgo = formatDistanceToNow(parseISO(note!.createdAt), {
    addSuffix: true,
  });

  return (
    <div className="flex min-h-screen flex-col bg-gray-50">
      {/* Header */}
      <header className="sticky top-0 z-30 border-b border-gray-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-2xl items-center justify-between px-4">
          <div className="flex items-center gap-2 min-w-0">
            <Link
              href="/dashboard"
              className="shrink-0 rounded-lg p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition-colors"
              aria-label="Back to dashboard"
            >
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div className="min-w-0">
              <p className="truncate font-semibold text-gray-900 text-sm">
                {note?.patientName || "Unknown Patient"}
              </p>
              <p className="text-xs text-gray-500">{timeAgo}</p>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {pollingActive && (
              <Spinner size="sm" label="Updating..." />
            )}
            <NoteStatusBadge status={note!.status} size="sm" />
          </div>
        </div>
      </header>

      <main className="flex-1">
        <div className="mx-auto max-w-2xl px-4 py-4 pb-32">
          {/* Note meta card */}
          <div className="mb-4 rounded-xl bg-white border border-gray-200 shadow-sm px-4 py-3">
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-sm text-gray-600">
              <span className="flex items-center gap-1.5">
                <User className="h-4 w-4 text-gray-400" />
                {note?.patientName || "Unknown Patient"}
              </span>
              <span className="flex items-center gap-1.5">
                <Calendar className="h-4 w-4 text-gray-400" />
                {visitDateFormatted}
              </span>
              <span className="flex items-center gap-1.5">
                <Clock className="h-4 w-4 text-gray-400" />
                {formatVisitType(note!.visitType)}
              </span>
            </div>

            {note?.confidenceScore !== undefined && (
              <div className="mt-3 flex items-center gap-2">
                <span className="text-xs text-gray-500">AI Confidence</span>
                <div className="flex-1 h-1.5 rounded-full bg-gray-100 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      note.confidenceScore >= 0.8
                        ? "bg-green-500"
                        : note.confidenceScore >= 0.6
                        ? "bg-amber-500"
                        : "bg-red-500"
                    }`}
                    style={{ width: `${Math.round(note.confidenceScore * 100)}%` }}
                  />
                </div>
                <span
                  className={`text-xs font-medium tabular-nums ${
                    note.confidenceScore >= 0.8
                      ? "text-green-600"
                      : note.confidenceScore >= 0.6
                      ? "text-amber-600"
                      : "text-red-600"
                  }`}
                >
                  {Math.round(note.confidenceScore * 100)}%
                </span>
              </div>
            )}
          </div>

          {/* Flags / warnings */}
          {note?.flags && note.flags.length > 0 && (
            <div className="mb-4 space-y-2">
              {note.flags.map((flag, i) => (
                <div
                  key={i}
                  className="flex items-start gap-2 rounded-lg bg-amber-50 border border-amber-200 px-3 py-2.5 text-sm text-amber-800"
                >
                  <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5 text-amber-500" />
                  {flag}
                </div>
              ))}
            </div>
          )}

          {/* Kinnser submission status */}
          {(note?.status === "submitted" || note?.kinnserStatus) && (
            <div
              className={`mb-4 rounded-lg border px-3 py-2.5 text-sm ${
                note?.kinnserError
                  ? "bg-red-50 border-red-200 text-red-700"
                  : "bg-green-50 border-green-200 text-green-700"
              }`}
            >
              <p className="font-medium flex items-center gap-1.5">
                {note?.kinnserError ? (
                  <AlertTriangle className="h-4 w-4" />
                ) : (
                  <CheckCircle className="h-4 w-4" />
                )}
                Kinnser:{" "}
                {note?.kinnserStatus || (note?.kinnserError ? "Error" : "Submitted")}
              </p>
              {note?.kinnserError && (
                <p className="mt-0.5 text-red-600">{note.kinnserError}</p>
              )}
              {note?.kinnserSubmissionId && (
                <p className="mt-0.5 text-xs text-green-600">
                  ID: {note.kinnserSubmissionId}
                </p>
              )}
            </div>
          )}

          {/* Processing state */}
          {isProcessing && (
            <div className="mb-4 flex items-center gap-3 rounded-xl bg-brand-50 border border-brand-200 px-4 py-4">
              <Loader2 className="h-6 w-6 text-brand-600 animate-spin shrink-0" />
              <div>
                <p className="text-sm font-semibold text-brand-800">
                  AI Processing in progress
                </p>
                <p className="text-xs text-brand-600 mt-0.5">
                  Transcribing and structuring your note...
                  <br />
                  This usually takes 30–90 seconds.
                </p>
              </div>
            </div>
          )}

          {/* Submit error */}
          {submitError && (
            <div className="mb-4 flex items-start gap-2 rounded-lg bg-red-50 border border-red-200 px-3 py-3 text-sm text-red-700">
              <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
              <p>{submitError}</p>
            </div>
          )}

          {/* Save success toast */}
          {saveSuccess && (
            <div className="mb-4 flex items-center gap-2 rounded-lg bg-green-50 border border-green-200 px-3 py-2.5 text-sm text-green-700">
              <CheckCircle className="h-4 w-4 shrink-0" />
              Changes saved
            </div>
          )}

          {/* SOAP Note Editor */}
          {note?.structuredNote || !isProcessing ? (
            <SOAPNoteEditor
              note={soapNote}
              onChange={setSoapNote}
              readOnly={isProcessing || note?.status === "submitted"}
            />
          ) : null}

          {/* Raw transcription (collapsed, for voice notes) */}
          {note?.rawTranscription && (
            <details className="mt-4 rounded-xl border border-gray-200 bg-white shadow-sm">
              <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-gray-600 hover:text-gray-900 select-none">
                Raw Transcription
              </summary>
              <div className="px-4 pb-4">
                <p className="text-sm text-gray-600 leading-relaxed whitespace-pre-wrap">
                  {note.rawTranscription}
                </p>
              </div>
            </details>
          )}
        </div>
      </main>

      {/* Sticky bottom action bar */}
      {!isProcessing && (
        <div className="fixed bottom-16 left-0 right-0 z-30 border-t border-gray-200 bg-white/95 backdrop-blur px-4 py-3 safe-area-pb">
          <div className="mx-auto flex max-w-2xl items-center gap-3">
            {canSubmit && note?.status !== "submitted" && (
              <Button
                variant="primary"
                size="md"
                onClick={handleApproveAndSubmit}
                loading={approving}
                leftIcon={<Send className="h-4 w-4" />}
                className="flex-1"
              >
                Approve & Submit to Kinnser
              </Button>
            )}

            {note && ["approved", "reviewed"].includes(note.status) && (
              <Button
                variant="secondary"
                size="md"
                onClick={handleSubmitToWellSky}
                loading={submitting}
                leftIcon={<Upload className="h-4 w-4" />}
                className="w-auto"
              >
                Submit to WellSky
              </Button>
            )}

            {note?.status !== "submitted" && (
              <Button
                variant={canSubmit ? "secondary" : "primary"}
                size="md"
                onClick={handleSave}
                loading={saving}
                leftIcon={
                  saveSuccess ? (
                    <CheckCircle className="h-4 w-4" />
                  ) : (
                    <Save className="h-4 w-4" />
                  )
                }
                className={canSubmit ? "w-auto" : "flex-1"}
              >
                {saveSuccess ? "Saved!" : "Save Changes"}
              </Button>
            )}

            <button
              type="button"
              onClick={() => loadNote()}
              className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition-colors"
              aria-label="Refresh note"
            >
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      <BottomNav />
    </div>
  );
}
