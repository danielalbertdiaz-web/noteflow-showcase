"use client";

import { Suspense, useState, useCallback, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, Mic, PenLine, Upload, CheckCircle, AlertCircle } from "lucide-react";
import Link from "next/link";
import { notesApi } from "@/lib/api";
import { VoiceRecorder } from "@/components/voice/VoiceRecorder";
import { Button } from "@/components/ui/Button";
import { Input, Textarea } from "@/components/ui/Input";
import { Header } from "@/components/layout/Header";
import { BottomNav } from "@/components/layout/BottomNav";
import { isAuthenticated } from "@/lib/auth";
import type { VisitType } from "@/types";

type InputMode = "voice" | "text";
type PageState = "idle" | "uploading" | "processing" | "success" | "error";

const VISIT_TYPE_OPTIONS: { value: VisitType; label: string }[] = [
  { value: "initial_eval", label: "Initial Evaluation" },
  { value: "follow_up", label: "Follow-up Visit" },
  { value: "re_eval", label: "Re-evaluation" },
  { value: "discharge", label: "Discharge" },
  { value: "recertification", label: "Recertification" },
  { value: "progress_note", label: "Progress Note" },
];

export default function NewNotePageWrapper() {
  return <Suspense fallback={<div>Loading...</div>}><NewNotePage /></Suspense>;
}

function NewNotePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialMode = (searchParams.get("mode") as InputMode) || "voice";

  const [mode, setMode] = useState<InputMode>(initialMode);
  const [pageState, setPageState] = useState<PageState>("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const [createdNoteId, setCreatedNoteId] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);

  // Shared fields
  const [patientName, setPatientName] = useState("");
  const [visitDate, setVisitDate] = useState(
    new Date().toISOString().split("T")[0]
  );
  const [visitType, setVisitType] = useState<VisitType>("follow_up");

  // Text mode specific
  const [rawText, setRawText] = useState("");
  const [autoSaveStatus, setAutoSaveStatus] = useState<"saved" | "saving" | "">("");

  // Voice mode
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);

  // Auth guard
  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/auth/login");
    }
  }, [router]);

  // Auto-save text draft to localStorage
  useEffect(() => {
    if (!rawText) return;
    setAutoSaveStatus("saving");
    const t = setTimeout(() => {
      localStorage.setItem("noteflow_text_draft", rawText);
      setAutoSaveStatus("saved");
      setTimeout(() => setAutoSaveStatus(""), 2000);
    }, 1000);
    return () => clearTimeout(t);
  }, [rawText]);

  // Restore draft on mount
  useEffect(() => {
    const draft = localStorage.getItem("noteflow_text_draft");
    if (draft && mode === "text") setRawText(draft);
  }, [mode]);

  const handleVoiceComplete = useCallback((blob: Blob) => {
    setAudioBlob(blob);
  }, []);

  const handleVoiceSubmit = async () => {
    if (!audioBlob) return;
    setPageState("uploading");
    setUploadProgress(0);
    setErrorMessage("");

    // Simulate upload progress feedback
    const progressInterval = setInterval(() => {
      setUploadProgress((p) => Math.min(p + 15, 85));
    }, 500);

    try {
      const note = await notesApi.createVoiceNote(audioBlob, {
        patientName: patientName.trim() || undefined,
        visitDate,
        visitType,
      });
      clearInterval(progressInterval);
      setUploadProgress(100);
      setCreatedNoteId(note.id);
      setPageState("success");
      localStorage.removeItem("noteflow_text_draft");
    } catch (err) {
      clearInterval(progressInterval);
      setPageState("error");
      setErrorMessage(
        err instanceof Error
          ? err.message
          : "Failed to upload recording. Please try again."
      );
    }
  };

  const handleTextSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rawText.trim()) return;

    setPageState("uploading");
    setErrorMessage("");

    try {
      const note = await notesApi.createTextNote({
        patientName: patientName.trim() || undefined,
        visitDate,
        visitType,
        rawText: rawText.trim(),
      });
      setCreatedNoteId(note.id);
      setPageState("success");
      localStorage.removeItem("noteflow_text_draft");
    } catch (err) {
      setPageState("error");
      setErrorMessage(
        err instanceof Error
          ? err.message
          : "Failed to create note. Please try again."
      );
    }
  };

  // Success screen
  if (pageState === "success" && createdNoteId) {
    return (
      <div className="flex min-h-screen flex-col bg-gray-50">
        <div className="flex flex-1 flex-col items-center justify-center px-4 py-12 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-green-100 mb-5">
            <CheckCircle className="h-8 w-8 text-green-600" />
          </div>
          <h2 className="text-xl font-bold text-gray-900">Note Submitted!</h2>
          <p className="mt-2 text-sm text-gray-500 max-w-xs">
            {mode === "voice"
              ? "Your recording is being processed by AI. This usually takes 30-60 seconds."
              : "Your note is being structured by AI. It will be ready to review shortly."}
          </p>
          <div className="mt-6 flex flex-col gap-3 w-full max-w-xs">
            <Link
              href={`/notes/${createdNoteId}`}
              className="flex items-center justify-center gap-2 rounded-lg bg-brand-600 px-5 py-3 text-sm font-medium text-white hover:bg-brand-700 transition-colors"
            >
              View Note
            </Link>
            <Link
              href="/dashboard"
              className="flex items-center justify-center gap-2 rounded-lg bg-white border border-gray-200 px-5 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Back to Dashboard
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const sharedFields = (
    <div className="space-y-4">
      <Input
        label="Patient Name"
        type="text"
        value={patientName}
        onChange={(e) => setPatientName(e.target.value)}
        placeholder="Jane Smith"
        helperText="Optional — can be added or edited later"
      />

      <div className="w-full">
        <label className="mb-1.5 block text-sm font-medium text-gray-700">
          Visit Type
        </label>
        <select
          value={visitType}
          onChange={(e) => setVisitType(e.target.value as VisitType)}
          className="form-field w-full"
        >
          {VISIT_TYPE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      <Input
        label="Visit Date"
        type="date"
        value={visitDate}
        onChange={(e) => setVisitDate(e.target.value)}
        required
      />
    </div>
  );

  return (
    <div className="flex min-h-screen flex-col bg-gray-50">
      {/* Custom slim header */}
      <header className="sticky top-0 z-30 border-b border-gray-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-2xl items-center gap-3 px-4">
          <Link
            href="/dashboard"
            className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition-colors"
            aria-label="Back to dashboard"
          >
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <h1 className="font-semibold text-gray-900">New Note</h1>
        </div>
      </header>

      <main className="flex-1">
        <div className="mx-auto max-w-2xl px-4 py-5 pb-28">
          {/* Mode toggle */}
          <div className="mb-6 flex rounded-xl bg-gray-100 p-1">
            <button
              type="button"
              onClick={() => setMode("voice")}
              className={`flex flex-1 items-center justify-center gap-2 rounded-lg py-2.5 text-sm font-medium transition-all ${
                mode === "voice"
                  ? "bg-white text-gray-900 shadow-sm"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              <Mic className="h-4 w-4" />
              Voice
            </button>
            <button
              type="button"
              onClick={() => setMode("text")}
              className={`flex flex-1 items-center justify-center gap-2 rounded-lg py-2.5 text-sm font-medium transition-all ${
                mode === "text"
                  ? "bg-white text-gray-900 shadow-sm"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              <PenLine className="h-4 w-4" />
              Text
            </button>
          </div>

          {/* Error banner */}
          {pageState === "error" && (
            <div className="mb-4 flex items-start gap-2 rounded-lg bg-red-50 border border-red-200 px-3 py-3 text-sm text-red-700">
              <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
              <div>
                <p className="font-medium">Submission failed</p>
                <p className="mt-0.5">{errorMessage}</p>
              </div>
            </div>
          )}

          {/* ── VOICE MODE ──────────────────────────────────── */}
          {mode === "voice" && (
            <div className="space-y-5">
              <div className="rounded-xl bg-white border border-gray-200 shadow-sm px-4 py-2">
                <VoiceRecorder
                  onRecordingComplete={handleVoiceComplete}
                />
              </div>

              {sharedFields}

              {/* Upload progress */}
              {pageState === "uploading" && (
                <div className="rounded-lg bg-brand-50 border border-brand-200 px-4 py-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-brand-700 flex items-center gap-2">
                      <Upload className="h-4 w-4 animate-bounce" />
                      Uploading recording...
                    </span>
                    <span className="text-sm text-brand-600 font-mono">
                      {uploadProgress}%
                    </span>
                  </div>
                  <div className="h-2 rounded-full bg-brand-100 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-brand-600 transition-all duration-300"
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                </div>
              )}

              <Button
                variant="primary"
                size="lg"
                fullWidth
                onClick={handleVoiceSubmit}
                disabled={!audioBlob || pageState === "uploading"}
                loading={pageState === "uploading"}
                leftIcon={<Upload className="h-4 w-4" />}
              >
                {audioBlob ? "Submit Recording" : "Record First"}
              </Button>
            </div>
          )}

          {/* ── TEXT MODE ───────────────────────────────────── */}
          {mode === "text" && (
            <form onSubmit={handleTextSubmit} className="space-y-5">
              <div className="relative">
                <Textarea
                  label="Clinical Note"
                  value={rawText}
                  onChange={(e) => setRawText(e.target.value)}
                  placeholder="Describe the patient encounter in your own words. Include subjective complaints, objective findings, your assessment, and plan. The AI will structure this into a SOAP note..."
                  rows={10}
                  required
                  className="min-h-[200px]"
                />
                {autoSaveStatus && (
                  <span className="absolute bottom-2 right-2 text-xs text-gray-400">
                    {autoSaveStatus === "saving" ? "Saving..." : "Draft saved"}
                  </span>
                )}
              </div>

              {sharedFields}

              <Button
                type="submit"
                variant="primary"
                size="lg"
                fullWidth
                loading={pageState === "uploading"}
                disabled={!rawText.trim() || pageState === "uploading"}
                leftIcon={<Upload className="h-4 w-4" />}
              >
                Submit for AI Processing
              </Button>
            </form>
          )}
        </div>
      </main>

      <BottomNav />
    </div>
  );
}
