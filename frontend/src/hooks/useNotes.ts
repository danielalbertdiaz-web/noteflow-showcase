"use client";

import { useState, useCallback } from "react";
import { notesApi } from "@/lib/api";
import type {
  Note,
  CreateTextNoteRequest,
  UpdateNoteRequest,
  SOAPNote,
} from "@/types";

interface UseNotesReturn {
  notes: Note[];
  total: number;
  loading: boolean;
  error: string | null;
  fetchNotes: (params?: {
    page?: number;
    pageSize?: number;
    status?: string;
    visitType?: string;
    search?: string;
  }) => Promise<void>;
  createVoiceNote: (
    audioBlob: Blob,
    metadata: {
      patientId?: string;
      patientName?: string;
      visitDate: string;
      visitType: string;
    }
  ) => Promise<Note>;
  createTextNote: (payload: CreateTextNoteRequest) => Promise<Note>;
  updateNote: (id: string, payload: UpdateNoteRequest) => Promise<Note>;
  updateSOAP: (id: string, soap: SOAPNote) => Promise<Note>;
  approveNote: (id: string) => Promise<Note>;
  deleteNote: (id: string) => Promise<void>;
}

export function useNotes(): UseNotesReturn {
  const [notes, setNotes] = useState<Note[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchNotes = useCallback(
    async (
      params?: Parameters<typeof notesApi.getNotes>[0]
    ) => {
      setLoading(true);
      setError(null);
      try {
        const result = await notesApi.getNotes(params);
        setNotes(result.notes);
        setTotal(result.total);
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to fetch notes";
        setError(message);
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const createVoiceNote = useCallback(
    async (
      audioBlob: Blob,
      metadata: {
        patientId?: string;
        patientName?: string;
        visitDate: string;
        visitType: string;
      }
    ): Promise<Note> => {
      const note = await notesApi.createVoiceNote(audioBlob, metadata);
      setNotes((prev) => [note, ...prev]);
      setTotal((prev) => prev + 1);
      return note;
    },
    []
  );

  const createTextNote = useCallback(
    async (payload: CreateTextNoteRequest): Promise<Note> => {
      const note = await notesApi.createTextNote(payload);
      setNotes((prev) => [note, ...prev]);
      setTotal((prev) => prev + 1);
      return note;
    },
    []
  );

  const updateNote = useCallback(
    async (id: string, payload: UpdateNoteRequest): Promise<Note> => {
      const updated = await notesApi.updateNote(id, payload);
      setNotes((prev) => prev.map((n) => (n.id === id ? updated : n)));
      return updated;
    },
    []
  );

  const updateSOAP = useCallback(
    async (id: string, soap: SOAPNote): Promise<Note> => {
      const updated = await notesApi.updateSOAPNote(id, soap);
      setNotes((prev) => prev.map((n) => (n.id === id ? updated : n)));
      return updated;
    },
    []
  );

  const approveNote = useCallback(async (id: string): Promise<Note> => {
    const updated = await notesApi.approveNote(id);
    setNotes((prev) => prev.map((n) => (n.id === id ? updated : n)));
    return updated;
  }, []);

  const deleteNote = useCallback(async (id: string): Promise<void> => {
    await notesApi.deleteNote(id);
    setNotes((prev) => prev.filter((n) => n.id !== id));
    setTotal((prev) => prev - 1);
  }, []);

  return {
    notes,
    total,
    loading,
    error,
    fetchNotes,
    createVoiceNote,
    createTextNote,
    updateNote,
    updateSOAP,
    approveNote,
    deleteNote,
  };
}
