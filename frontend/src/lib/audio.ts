// ─── Audio Utilities for NoteFlow ───────────────────────────

const DB_NAME = "noteflow-audio";
const DB_VERSION = 1;
const STORE_NAME = "recordings";

// ─── IndexedDB Setup ─────────────────────────────────────────

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const store = db.createObjectStore(STORE_NAME, { keyPath: "id" });
        store.createIndex("createdAt", "createdAt", { unique: false });
      }
    };

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export interface AudioRecord {
  id: string;
  blob: Blob;
  mimeType: string;
  durationSeconds?: number;
  metadata: {
    patientName?: string;
    visitDate?: string;
    visitType?: string;
  };
  createdAt: number;
  synced: boolean;
}

export async function saveToIndexedDB(record: AudioRecord): Promise<string> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    const store = tx.objectStore(STORE_NAME);
    const request = store.put(record);
    request.onsuccess = () => resolve(record.id);
    request.onerror = () => reject(request.error);
  });
}

export async function loadFromIndexedDB(
  id: string
): Promise<AudioRecord | null> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readonly");
    const store = tx.objectStore(STORE_NAME);
    const request = store.get(id);
    request.onsuccess = () => resolve(request.result as AudioRecord | null);
    request.onerror = () => reject(request.error);
  });
}

export async function getPendingRecordings(): Promise<AudioRecord[]> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readonly");
    const store = tx.objectStore(STORE_NAME);
    const request = store.getAll();
    request.onsuccess = () => {
      const records = (request.result as AudioRecord[]).filter(
        (r) => !r.synced
      );
      resolve(records);
    };
    request.onerror = () => reject(request.error);
  });
}

export async function markAsSynced(id: string): Promise<void> {
  const db = await openDB();
  const record = await loadFromIndexedDB(id);
  if (!record) return;

  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    const store = tx.objectStore(STORE_NAME);
    const request = store.put({ ...record, synced: true });
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}

export async function deleteFromIndexedDB(id: string): Promise<void> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    const store = tx.objectStore(STORE_NAME);
    const request = store.delete(id);
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}

// ─── AudioRecorder Class ─────────────────────────────────────

export type RecorderEventType =
  | "start"
  | "stop"
  | "pause"
  | "resume"
  | "dataavailable"
  | "error";

type RecorderHandler = (data?: unknown) => void;

export class AudioRecorder {
  private mediaRecorder: MediaRecorder | null = null;
  private stream: MediaStream | null = null;
  private chunks: Blob[] = [];
  private listeners: Partial<Record<RecorderEventType, RecorderHandler[]>> = {};
  private startTime = 0;
  private timerInterval: ReturnType<typeof setInterval> | null = null;
  public duration = 0;

  get isRecording(): boolean {
    return this.mediaRecorder?.state === "recording";
  }

  get isPaused(): boolean {
    return this.mediaRecorder?.state === "paused";
  }

  on(event: RecorderEventType, handler: RecorderHandler): this {
    if (!this.listeners[event]) this.listeners[event] = [];
    this.listeners[event]!.push(handler);
    return this;
  }

  private emit(event: RecorderEventType, data?: unknown) {
    this.listeners[event]?.forEach((h) => h(data));
  }

  async start(): Promise<void> {
    if (this.isRecording) return;

    const permission = await checkMicrophonePermission();
    if (!permission) {
      this.emit("error", new Error("Microphone permission denied"));
      throw new Error("Microphone permission denied");
    }

    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        sampleRate: 16000,
        channelCount: 1,
      },
    });

    const mimeType = getSupportedMimeType();
    this.mediaRecorder = new MediaRecorder(this.stream, { mimeType });
    this.chunks = [];

    this.mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) {
        this.chunks.push(e.data);
        this.emit("dataavailable", e.data);
      }
    };

    this.mediaRecorder.onstop = () => {
      const blob = new Blob(this.chunks, { type: mimeType });
      this.emit("stop", blob);
      this.stopTimer();
      this.releaseStream();
    };

    this.mediaRecorder.onerror = (e) => {
      this.emit("error", e);
    };

    this.mediaRecorder.start(1000); // collect chunks every 1s
    this.startTime = Date.now();
    this.startTimer();
    this.emit("start");
  }

  stop(): void {
    if (!this.isRecording && !this.isPaused) return;
    this.mediaRecorder?.stop();
  }

  pause(): void {
    if (!this.isRecording) return;
    this.mediaRecorder?.pause();
    this.stopTimer();
    this.emit("pause");
  }

  resume(): void {
    if (!this.isPaused) return;
    this.mediaRecorder?.resume();
    this.startTimer();
    this.emit("resume");
  }

  private startTimer() {
    this.timerInterval = setInterval(() => {
      this.duration = Math.floor((Date.now() - this.startTime) / 1000);
    }, 500);
  }

  private stopTimer() {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
  }

  private releaseStream() {
    this.stream?.getTracks().forEach((t) => t.stop());
    this.stream = null;
  }

  destroy() {
    this.stop();
    this.releaseStream();
    this.listeners = {};
  }
}

// ─── Helpers ─────────────────────────────────────────────────

export function getSupportedMimeType(): string {
  const types = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/ogg;codecs=opus",
    "audio/ogg",
    "audio/mp4",
  ];
  for (const type of types) {
    if (MediaRecorder.isTypeSupported(type)) return type;
  }
  return "audio/webm";
}

export async function checkMicrophonePermission(): Promise<boolean> {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    return false;
  }
  try {
    const result = await navigator.permissions.query({
      name: "microphone" as PermissionName,
    });
    if (result.state === "denied") return false;
    return true;
  } catch {
    // permissions API not supported - try directly
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach((t) => t.stop());
      return true;
    } catch {
      return false;
    }
  }
}

export function getAudioDuration(blob: Blob): Promise<number> {
  return new Promise((resolve, reject) => {
    const audio = new Audio();
    const url = URL.createObjectURL(blob);
    audio.src = url;
    audio.onloadedmetadata = () => {
      URL.revokeObjectURL(url);
      resolve(audio.duration);
    };
    audio.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("Could not determine audio duration"));
    };
  });
}

export function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60)
    .toString()
    .padStart(2, "0");
  const s = (seconds % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

export function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}
