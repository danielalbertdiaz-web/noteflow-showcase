// ============================================================
// NoteFlow TypeScript Types
// Matches backend schemas exactly
// ============================================================

export type NoteStatus =
  | "draft"
  | "processing"
  | "transcribed"
  | "structured"
  | "reviewed"
  | "approved"
  | "submitted"
  | "failed";

export type VisitType =
  | "initial_eval"
  | "follow_up"
  | "re_eval"
  | "discharge"
  | "recertification"
  | "progress_note";

export type InputMode = "voice" | "text";

// ─── User & Auth ────────────────────────────────────────────

export interface User {
  id: string;
  email: string;
  role: "clinician" | "supervisor" | "admin";
  clinician?: Clinician;
  agency?: Agency;
  createdAt: string;
}

export interface Agency {
  id: string;
  name: string;
  kinnserDomain?: string;
  kinnserUsername?: string;
  isActive: boolean;
}

export interface Clinician {
  id: string;
  userId: string;
  firstName: string;
  lastName: string;
  fullName: string;
  licenseNumber?: string;
  npi?: string;
  credential?: string;
  agencyId: string;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
  expiresIn: number;
}

// ─── SOAP Note Structures ────────────────────────────────────

export interface VitalSigns {
  bloodPressure?: string;
  heartRate?: number;
  respiratoryRate?: number;
  temperature?: number;
  oxygenSaturation?: number;
  weight?: number;
  height?: number;
  bmi?: number;
  painScale?: number;
}

export interface ROMMeasurement {
  joint: string;
  movement: string;
  activeRom?: number;
  passiveRom?: number;
  normalRom?: number;
  side?: "left" | "right" | "bilateral";
  notes?: string;
}

export interface StrengthTest {
  muscleGroup: string;
  side?: "left" | "right" | "bilateral";
  grade?: number;
  gradeLabel?: string;
  notes?: string;
}

export interface FunctionalAssessment {
  transfers?: string;
  ambulation?: string;
  stairs?: string;
  adls?: string;
  balance?: string;
  balanceScore?: number;
  fallRisk?: "low" | "moderate" | "high";
  mobilityDevice?: string;
  weightBearingStatus?: string;
}

export interface Subjective {
  chiefComplaint?: string;
  patientReportedSymptoms?: string;
  painLocation?: string;
  painQuality?: string;
  painScale?: number;
  painBehavior?: string;
  aggravatingFactors?: string;
  relievingFactors?: string;
  priorLevelOfFunction?: string;
  patientGoals?: string;
  medicalHistory?: string;
  currentMedications?: string;
  socialHistory?: string;
  livingSituation?: string;
  precautions?: string;
}

export interface Objective {
  vitalSigns?: VitalSigns;
  observation?: string;
  posture?: string;
  gait?: string;
  romMeasurements?: ROMMeasurement[];
  strengthTests?: StrengthTest[];
  functionalAssessment?: FunctionalAssessment;
  specialTests?: string;
  palpation?: string;
  neurovascularStatus?: string;
  woundAssessment?: string;
  edema?: string;
}

export interface Assessment {
  diagnosis?: string;
  clinicalImpression?: string;
  functionalLimitations?: string;
  prognosticFactors?: string;
  rehabilitationPotential?: "excellent" | "good" | "fair" | "poor";
  goalsStatus?: string;
  shortTermGoals?: string[];
  longTermGoals?: string[];
  icdCodes?: string[];
}

export interface Plan {
  treatmentProvided?: string;
  treatmentTechniques?: string[];
  homeExerciseProgram?: string;
  patientEducation?: string;
  frequencyDuration?: string;
  nextVisitPlan?: string;
  referrals?: string;
  equipmentOrdered?: string;
  followUpDate?: string;
  additionalNotes?: string;
}

export interface OASISFields {
  m1800?: string;
  m1810?: string;
  m1820?: string;
  m1830?: string;
  m1840?: string;
  m1850?: string;
  m1860?: string;
  [key: string]: string | undefined;
}

export interface SOAPNote {
  subjective?: Subjective;
  objective?: Objective;
  assessment?: Assessment;
  plan?: Plan;
  oasisFields?: OASISFields;
}

// ─── Note ────────────────────────────────────────────────────

export interface Note {
  id: string;
  clinicianId: string;
  agencyId: string;
  patientId?: string;
  patientName?: string;
  visitDate: string;
  visitType: VisitType;
  inputMode: InputMode;
  status: NoteStatus;
  rawTranscription?: string;
  rawText?: string;
  structuredNote?: SOAPNote;
  confidenceScore?: number;
  flags?: string[];
  audioFileUrl?: string;
  audioDurationSeconds?: number;
  processingTimeMs?: number;
  kinnserSubmissionId?: string;
  kinnserStatus?: string;
  kinnserError?: string;
  submittedAt?: string;
  reviewedAt?: string;
  approvedAt?: string;
  createdAt: string;
  updatedAt: string;
}

// ─── API Request/Response Types ──────────────────────────────

export interface CreateTextNoteRequest {
  patientId?: string;
  patientName?: string;
  visitDate: string;
  visitType: VisitType;
  rawText: string;
}

export interface UpdateNoteRequest {
  patientName?: string;
  visitDate?: string;
  visitType?: VisitType;
  structuredNote?: SOAPNote;
}

export interface NoteListResponse {
  notes: Note[];
  total: number;
  page: number;
  pageSize: number;
}

export interface NoteStatusResponse {
  id: string;
  status: NoteStatus;
  processingProgress?: number;
  kinnserStatus?: string;
  kinnserError?: string;
}

export interface ApiError {
  detail: string;
  statusCode?: number;
}

// ─── UI State Types ──────────────────────────────────────────

export interface DashboardStats {
  totalNotes: number;
  pendingReview: number;
  submittedToday: number;
  processingNotes: number;
}

export interface RecordingState {
  isRecording: boolean;
  isPaused: boolean;
  duration: number;
  audioBlob: Blob | null;
  error: string | null;
}
