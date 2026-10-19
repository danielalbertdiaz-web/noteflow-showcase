"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { AudioRecorder } from "@/lib/audio";

interface UseVoiceRecorderReturn {
  isRecording: boolean;
  isPaused: boolean;
  duration: number;
  audioBlob: Blob | null;
  error: string | null;
  startRecording: () => Promise<void>;
  stopRecording: () => void;
  pauseRecording: () => void;
  resumeRecording: () => void;
  resetRecording: () => void;
}

export function useVoiceRecorder(): UseVoiceRecorderReturn {
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [duration, setDuration] = useState(0);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [error, setError] = useState<string | null>(null);

  const recorderRef = useRef<AudioRecorder | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTimeRef = useRef<number>(0);
  const pausedDurationRef = useRef<number>(0);

  const startTimer = useCallback(() => {
    startTimeRef.current = Date.now();
    timerRef.current = setInterval(() => {
      const elapsed = Math.floor(
        (Date.now() - startTimeRef.current) / 1000 + pausedDurationRef.current
      );
      setDuration(elapsed);
    }, 500);
  }, []);

  const stopTimer = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const startRecording = useCallback(async () => {
    setError(null);
    setAudioBlob(null);
    setDuration(0);
    pausedDurationRef.current = 0;

    const recorder = new AudioRecorder();
    recorderRef.current = recorder;

    recorder.on("start", () => {
      setIsRecording(true);
      setIsPaused(false);
      startTimer();
    });

    recorder.on("stop", (blob) => {
      setIsRecording(false);
      setIsPaused(false);
      setAudioBlob(blob as Blob);
      stopTimer();
    });

    recorder.on("pause", () => {
      setIsPaused(true);
      pausedDurationRef.current = duration;
      stopTimer();
    });

    recorder.on("resume", () => {
      setIsPaused(false);
      startTimer();
    });

    recorder.on("error", (err) => {
      const msg =
        err instanceof Error ? err.message : "Recording error occurred";
      setError(msg);
      setIsRecording(false);
      setIsPaused(false);
      stopTimer();
    });

    try {
      await recorder.start();
    } catch (err) {
      const msg =
        err instanceof Error
          ? err.message
          : "Failed to start recording. Check microphone permissions.";
      setError(msg);
    }
  }, [duration, startTimer, stopTimer]);

  const stopRecording = useCallback(() => {
    recorderRef.current?.stop();
  }, []);

  const pauseRecording = useCallback(() => {
    recorderRef.current?.pause();
  }, []);

  const resumeRecording = useCallback(() => {
    recorderRef.current?.resume();
  }, []);

  const resetRecording = useCallback(() => {
    recorderRef.current?.destroy();
    recorderRef.current = null;
    stopTimer();
    setIsRecording(false);
    setIsPaused(false);
    setDuration(0);
    setAudioBlob(null);
    setError(null);
    pausedDurationRef.current = 0;
  }, [stopTimer]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      recorderRef.current?.destroy();
      stopTimer();
    };
  }, [stopTimer]);

  return {
    isRecording,
    isPaused,
    duration,
    audioBlob,
    error,
    startRecording,
    stopRecording,
    pauseRecording,
    resumeRecording,
    resetRecording,
  };
}
