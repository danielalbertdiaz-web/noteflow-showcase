"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Mic,
  PenLine,
  FileText,
  Clock,
  CheckCheck,
  Loader2,
  RefreshCw,
  ChevronRight,
} from "lucide-react";
import { notesApi } from "@/lib/api";
import { NoteCard } from "@/components/notes/NoteCard";
import { Spinner } from "@/components/ui/Spinner";
import { Button } from "@/components/ui/Button";
import type { Note, DashboardStats } from "@/types";

export default function DashboardPage() {
  const router = useRouter();
  const [notes, setNotes] = useState<Note[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    setError(null);

    try {
      const [notesRes, statsRes] = await Promise.allSettled([
        notesApi.getNotes({ pageSize: 10 }),
        notesApi.getDashboardStats(),
      ]);

      if (notesRes.status === "fulfilled") {
        setNotes(notesRes.value.notes);
      }
      if (statsRes.status === "fulfilled") {
        setStats(statsRes.value);
      }

      if (notesRes.status === "rejected" && statsRes.status === "rejected") {
        setError("Failed to load dashboard. Pull down to refresh.");
      }
    } catch {
      setError("Failed to load dashboard data.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Poll for processing notes every 10s
  useEffect(() => {
    const hasProcessing = notes.some(
      (n) => n.status === "processing" || n.status === "transcribed"
    );
    if (!hasProcessing) return;

    const interval = setInterval(() => {
      loadData(true);
    }, 10000);

    return () => clearInterval(interval);
  }, [notes]);

  const statCards = [
    {
      label: "Total Notes",
      value: stats?.totalNotes ?? "-",
      icon: FileText,
      color: "text-brand-600",
      bg: "bg-brand-50",
    },
    {
      label: "Pending Review",
      value: stats?.pendingReview ?? "-",
      icon: Clock,
      color: "text-amber-600",
      bg: "bg-amber-50",
    },
    {
      label: "Submitted Today",
      value: stats?.submittedToday ?? "-",
      icon: CheckCheck,
      color: "text-green-600",
      bg: "bg-green-50",
    },
  ];

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <Spinner size="lg" />
        <p className="mt-3 text-sm text-gray-500">Loading dashboard...</p>
      </div>
    );
  }

  return (
    <div className="page-container">
      {/* Greeting */}
      <div className="mb-6">
        <h1 className="text-xl font-bold text-gray-900">
          Good{" "}
          {new Date().getHours() < 12
            ? "morning"
            : new Date().getHours() < 17
            ? "afternoon"
            : "evening"}
        </h1>
        <p className="mt-0.5 text-sm text-gray-500">
          {new Date().toLocaleDateString("en-US", {
            weekday: "long",
            month: "long",
            day: "numeric",
          })}
        </p>
      </div>

      {/* Stats row */}
      <div className="mb-6 grid grid-cols-3 gap-3">
        {statCards.map((card) => {
          const Icon = card.icon;
          return (
            <div key={card.label} className="stat-card">
              <div
                className={`mb-2 inline-flex h-8 w-8 items-center justify-center rounded-lg ${card.bg}`}
              >
                <Icon className={`h-4 w-4 ${card.color}`} />
              </div>
              <p className="stat-value text-xl">{card.value}</p>
              <p className="stat-label">{card.label}</p>
            </div>
          );
        })}
      </div>

      {/* Processing indicator */}
      {stats?.processingNotes && stats.processingNotes > 0 ? (
        <div className="mb-4 flex items-center gap-2 rounded-lg bg-blue-50 border border-blue-200 px-3 py-2.5 text-sm text-blue-700">
          <Loader2 className="h-4 w-4 animate-spin shrink-0" />
          <span>
            {stats.processingNotes} note
            {stats.processingNotes > 1 ? "s" : ""} being processed by AI
          </span>
        </div>
      ) : null}

      {/* Quick actions */}
      <div className="mb-6">
        <div className="section-header">
          <h2 className="section-title">Quick Actions</h2>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Link
            href="/notes/new?mode=voice"
            className="flex flex-col items-center gap-3 rounded-xl bg-brand-600 px-4 py-5 text-white shadow-sm hover:bg-brand-700 active:bg-brand-800 transition-colors"
          >
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-white/20">
              <Mic className="h-6 w-6" />
            </div>
            <div className="text-center">
              <p className="font-semibold text-sm">Voice Note</p>
              <p className="text-xs text-brand-100 mt-0.5">Dictate & AI-structure</p>
            </div>
          </Link>

          <Link
            href="/notes/new?mode=text"
            className="flex flex-col items-center gap-3 rounded-xl bg-white border border-gray-200 px-4 py-5 text-gray-900 shadow-sm hover:bg-gray-50 active:bg-gray-100 transition-colors"
          >
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-50">
              <PenLine className="h-6 w-6 text-brand-600" />
            </div>
            <div className="text-center">
              <p className="font-semibold text-sm">Text Note</p>
              <p className="text-xs text-gray-500 mt-0.5">Type your note</p>
            </div>
          </Link>
        </div>
      </div>

      {/* Recent notes */}
      <div>
        <div className="section-header">
          <h2 className="section-title">Recent Notes</h2>
          <div className="flex items-center gap-2">
            {refreshing && <Spinner size="sm" />}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => loadData(true)}
              leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
              disabled={refreshing}
            >
              Refresh
            </Button>
          </div>
        </div>

        {error && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {!error && notes.length === 0 && (
          <div className="rounded-xl border border-dashed border-gray-300 bg-white py-12 text-center">
            <FileText className="mx-auto h-8 w-8 text-gray-300 mb-3" />
            <p className="font-medium text-gray-600">No notes yet</p>
            <p className="mt-1 text-sm text-gray-400">
              Start by creating your first note
            </p>
            <Link
              href="/notes/new"
              className="mt-4 inline-flex items-center gap-1.5 text-sm text-brand-600 hover:text-brand-700 font-medium"
            >
              Create a note
              <ChevronRight className="h-4 w-4" />
            </Link>
          </div>
        )}

        {notes.length > 0 && (
          <div className="rounded-xl border border-gray-200 bg-white overflow-hidden shadow-sm divide-y divide-gray-100">
            {notes.map((note) => (
              <NoteCard key={note.id} note={note} />
            ))}
            <div className="px-4 py-3 text-center">
              <button
                type="button"
                onClick={() => router.push("/notes")}
                className="text-sm text-brand-600 hover:text-brand-700 font-medium"
              >
                View all notes
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
