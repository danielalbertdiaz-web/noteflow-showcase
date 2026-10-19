"use client";

import React from "react";
import { Mic, Square, Pause, Play, RotateCcw, AlertCircle } from "lucide-react";
import { useVoiceRecorder } from "@/hooks/useVoiceRecorder";
import { formatDuration } from "@/lib/audio";
import { cn } from "@/lib/utils";

interface VoiceRecorderProps {
  onRecordingComplete: (blob: Blob) => void;
  className?: string;
}

export function VoiceRecorder({
  onRecordingComplete,
  className,
}: VoiceRecorderProps) {
  const {
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
  } = useVoiceRecorder();

  // When a blob is ready, notify parent
  React.useEffect(() => {
    if (audioBlob) {
      onRecordingComplete(audioBlob);
    }
  }, [audioBlob, onRecordingComplete]);

  const handleMainButton = async () => {
    if (!isRecording && !isPaused) {
      await startRecording();
    } else {
      stopRecording();
    }
  };

  const WaveformBars = () => (
    <div className="flex items-center justify-center gap-1 h-10" aria-hidden="true">
      {Array.from({ length: 9 }).map((_, i) => (
        <div
          key={i}
          className={cn(
            "w-1.5 rounded-full bg-brand-400 transition-all",
            isRecording && !isPaused
              ? "animate-wave"
              : "h-2 bg-gray-200"
          )}
          style={
            isRecording && !isPaused
              ? { animationDelay: `${i * 0.08}s`, height: `${Math.random() * 24 + 8}px` }
              : {}
          }
        />
      ))}
    </div>
  );

  return (
    <div className={cn("flex flex-col items-center gap-6 py-4", className)}>
      {/* Error state */}
      {error && (
        <div className="flex items-start gap-2 rounded-lg bg-red-50 border border-red-200 p-3 text-sm text-red-700 w-full">
          <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
          <div>
            <p className="font-medium">Microphone Error</p>
            <p className="mt-0.5 text-red-600">{error}</p>
            <p className="mt-1 text-xs">
              Please allow microphone access in your browser settings.
            </p>
          </div>
        </div>
      )}

      {/* Waveform */}
      <WaveformBars />

      {/* Timer */}
      <div className="text-3xl font-mono font-semibold text-gray-900 tabular-nums">
        {formatDuration(duration)}
      </div>

      {/* Status text */}
      <p className="text-sm text-gray-500">
        {!isRecording && !isPaused && !audioBlob && "Tap to start recording"}
        {isRecording && "Recording... tap to stop"}
        {isPaused && "Paused"}
        {audioBlob && "Recording complete"}
      </p>

      {/* Main record/stop button */}
      <div className="relative">
        {(isRecording || isPaused) && (
          <span
            className="absolute inset-0 rounded-full bg-red-400 opacity-30 animate-pulse-ring"
            aria-hidden="true"
          />
        )}
        <button
          type="button"
          onClick={handleMainButton}
          disabled={!!audioBlob}
          className={cn(
            "relative flex h-20 w-20 items-center justify-center rounded-full shadow-lg transition-all",
            "focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-offset-2",
            !isRecording && !isPaused && !audioBlob
              ? "bg-brand-600 hover:bg-brand-700 active:scale-95 focus-visible:ring-brand-500 text-white"
              : isRecording || isPaused
              ? "bg-red-500 hover:bg-red-600 active:scale-95 focus-visible:ring-red-500 text-white"
              : "bg-gray-200 text-gray-400 cursor-not-allowed"
          )}
          aria-label={
            isRecording ? "Stop recording" : isPaused ? "Stop recording" : "Start recording"
          }
        >
          {isRecording || isPaused ? (
            <Square className="h-8 w-8" />
          ) : (
            <Mic className="h-8 w-8" />
          )}
        </button>
      </div>

      {/* Secondary controls */}
      {(isRecording || isPaused) && (
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={isPaused ? resumeRecording : pauseRecording}
            className="flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 transition-colors"
          >
            {isPaused ? (
              <>
                <Play className="h-4 w-4" />
                Resume
              </>
            ) : (
              <>
                <Pause className="h-4 w-4" />
                Pause
              </>
            )}
          </button>
        </div>
      )}

      {/* Reset button after completion */}
      {audioBlob && (
        <button
          type="button"
          onClick={resetRecording}
          className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors"
        >
          <RotateCcw className="h-4 w-4" />
          Record again
        </button>
      )}
    </div>
  );
}
