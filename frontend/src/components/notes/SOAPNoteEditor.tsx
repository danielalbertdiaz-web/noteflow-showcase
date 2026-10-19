"use client";

import React, { useState, useCallback } from "react";
import {
  MessageSquare,
  Activity,
  Brain,
  ClipboardList,
  Edit3,
  Check,
  X,
} from "lucide-react";
import { CollapsibleCard } from "@/components/ui/Card";
import type {
  SOAPNote,
  Subjective,
  Objective,
  Assessment,
  Plan,
  ROMMeasurement,
  StrengthTest,
  VitalSigns,
} from "@/types";

interface SOAPNoteEditorProps {
  note: SOAPNote;
  onChange?: (updated: SOAPNote) => void;
  readOnly?: boolean;
}

// ─── Inline editable field ──────────────────────────────────

interface EditableFieldProps {
  label: string;
  value: string | number | undefined;
  onSave: (value: string) => void;
  readOnly?: boolean;
  multiline?: boolean;
  type?: "text" | "number";
}

function EditableField({
  label,
  value,
  onSave,
  readOnly = false,
  multiline = false,
  type = "text",
}: EditableFieldProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(String(value ?? ""));

  const handleSave = () => {
    onSave(draft);
    setEditing(false);
  };

  const handleCancel = () => {
    setDraft(String(value ?? ""));
    setEditing(false);
  };

  const handleKeyDown = (
    e: React.KeyboardEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    if (e.key === "Enter" && !multiline) {
      e.preventDefault();
      handleSave();
    }
    if (e.key === "Escape") handleCancel();
  };

  const displayValue = value !== undefined && value !== "" ? String(value) : null;

  return (
    <div className="group">
      <dt className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
        {label}
      </dt>
      <dd>
        {editing ? (
          <div className="flex items-start gap-2">
            {multiline ? (
              <textarea
                autoFocus
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={handleKeyDown}
                className="flex-1 min-h-[80px] resize-y rounded-lg border border-brand-300 bg-brand-50 px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            ) : (
              <input
                autoFocus
                type={type}
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={handleKeyDown}
                className="flex-1 rounded-lg border border-brand-300 bg-brand-50 px-3 py-1.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            )}
            <div className="flex gap-1 shrink-0 pt-0.5">
              <button
                type="button"
                onClick={handleSave}
                className="rounded-md p-1.5 text-green-600 hover:bg-green-50 transition-colors"
                aria-label="Save"
              >
                <Check className="h-4 w-4" />
              </button>
              <button
                type="button"
                onClick={handleCancel}
                className="rounded-md p-1.5 text-gray-400 hover:bg-gray-100 transition-colors"
                aria-label="Cancel"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>
        ) : (
          <div
            className={`flex items-start gap-2 rounded-lg px-2 py-1.5 -mx-2 ${
              readOnly
                ? ""
                : "hover:bg-gray-50 cursor-pointer group-hover:ring-1 group-hover:ring-transparent"
            }`}
            onClick={() => !readOnly && setEditing(true)}
          >
            <p className="flex-1 text-sm text-gray-900 min-h-[1.5rem]">
              {displayValue ?? (
                <span className="text-gray-400 italic">
                  {readOnly ? "Not documented" : "Click to add..."}
                </span>
              )}
            </p>
            {!readOnly && (
              <Edit3 className="h-3.5 w-3.5 text-gray-300 shrink-0 mt-0.5 opacity-0 group-hover:opacity-100 transition-opacity" />
            )}
          </div>
        )}
      </dd>
    </div>
  );
}

// ─── Vital Signs Grid ────────────────────────────────────────

function VitalSignsSection({
  vitals,
  onChange,
  readOnly,
}: {
  vitals: VitalSigns | undefined;
  onChange: (updated: VitalSigns) => void;
  readOnly?: boolean;
}) {
  const update = (key: keyof VitalSigns, value: string) => {
    const numVal = value === "" ? undefined : Number(value);
    onChange({ ...vitals, [key]: numVal });
  };
  const updateStr = (key: keyof VitalSigns, value: string) => {
    onChange({ ...vitals, [key]: value || undefined });
  };

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
      <div className="rounded-lg bg-gray-50 px-3 py-2.5">
        <EditableField
          label="Blood Pressure"
          value={vitals?.bloodPressure}
          onSave={(v) => updateStr("bloodPressure", v)}
          readOnly={readOnly}
        />
      </div>
      <div className="rounded-lg bg-gray-50 px-3 py-2.5">
        <EditableField
          label="Heart Rate"
          value={vitals?.heartRate}
          onSave={(v) => update("heartRate", v)}
          readOnly={readOnly}
          type="number"
        />
      </div>
      <div className="rounded-lg bg-gray-50 px-3 py-2.5">
        <EditableField
          label="O2 Saturation %"
          value={vitals?.oxygenSaturation}
          onSave={(v) => update("oxygenSaturation", v)}
          readOnly={readOnly}
          type="number"
        />
      </div>
      <div className="rounded-lg bg-gray-50 px-3 py-2.5">
        <EditableField
          label="Pain Scale (0-10)"
          value={vitals?.painScale}
          onSave={(v) => update("painScale", v)}
          readOnly={readOnly}
          type="number"
        />
      </div>
      <div className="rounded-lg bg-gray-50 px-3 py-2.5">
        <EditableField
          label="Weight (lbs)"
          value={vitals?.weight}
          onSave={(v) => update("weight", v)}
          readOnly={readOnly}
          type="number"
        />
      </div>
      <div className="rounded-lg bg-gray-50 px-3 py-2.5">
        <EditableField
          label="Resp Rate"
          value={vitals?.respiratoryRate}
          onSave={(v) => update("respiratoryRate", v)}
          readOnly={readOnly}
          type="number"
        />
      </div>
    </div>
  );
}

// ─── ROM Table ───────────────────────────────────────────────

function ROMTable({
  measurements,
  onChange,
  readOnly,
}: {
  measurements: ROMMeasurement[] | undefined;
  onChange: (updated: ROMMeasurement[]) => void;
  readOnly?: boolean;
}) {
  if (!measurements?.length && readOnly) {
    return <p className="text-sm text-gray-400 italic">No ROM data recorded</p>;
  }

  return (
    <div className="overflow-x-auto -mx-2">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200">
            <th className="pb-2 pr-3 text-left text-xs font-medium text-gray-500 uppercase">
              Joint / Movement
            </th>
            <th className="pb-2 px-2 text-center text-xs font-medium text-gray-500 uppercase">
              Side
            </th>
            <th className="pb-2 px-2 text-right text-xs font-medium text-gray-500 uppercase">
              Active
            </th>
            <th className="pb-2 px-2 text-right text-xs font-medium text-gray-500 uppercase">
              Passive
            </th>
            <th className="pb-2 pl-2 text-right text-xs font-medium text-gray-500 uppercase">
              Normal
            </th>
          </tr>
        </thead>
        <tbody>
          {measurements?.map((m, i) => (
            <tr key={i} className="border-b border-gray-100 last:border-0">
              <td className="py-2 pr-3 font-medium text-gray-900">
                {m.joint} - {m.movement}
              </td>
              <td className="py-2 px-2 text-center text-gray-600 capitalize">
                {m.side || "-"}
              </td>
              <td className="py-2 px-2 text-right text-gray-900">
                {m.activeRom !== undefined ? `${m.activeRom}°` : "-"}
              </td>
              <td className="py-2 px-2 text-right text-gray-900">
                {m.passiveRom !== undefined ? `${m.passiveRom}°` : "-"}
              </td>
              <td className="py-2 pl-2 text-right text-gray-500">
                {m.normalRom !== undefined ? `${m.normalRom}°` : "-"}
              </td>
            </tr>
          ))}
          {(!measurements || measurements.length === 0) && (
            <tr>
              <td colSpan={5} className="py-3 text-center text-gray-400 italic text-xs">
                No ROM measurements documented
              </td>
            </tr>
          )}
        </tbody>
      </table>
      {!readOnly && (
        <button
          type="button"
          onClick={() => {
            const newMeasurement: ROMMeasurement = {
              joint: "Shoulder",
              movement: "Flexion",
              side: "right",
              activeRom: 0,
              normalRom: 180,
            };
            onChange([...(measurements || []), newMeasurement]);
          }}
          className="mt-2 text-xs text-brand-600 hover:text-brand-700 font-medium"
        >
          + Add measurement
        </button>
      )}
    </div>
  );
}

// ─── Strength Table ──────────────────────────────────────────

function StrengthTable({
  tests,
}: {
  tests: StrengthTest[] | undefined;
  readOnly?: boolean;
}) {
  if (!tests?.length) {
    return (
      <p className="text-sm text-gray-400 italic">
        No strength tests documented
      </p>
    );
  }

  return (
    <div className="overflow-x-auto -mx-2">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200">
            <th className="pb-2 pr-3 text-left text-xs font-medium text-gray-500 uppercase">
              Muscle Group
            </th>
            <th className="pb-2 px-2 text-center text-xs font-medium text-gray-500 uppercase">
              Side
            </th>
            <th className="pb-2 pl-2 text-right text-xs font-medium text-gray-500 uppercase">
              Grade
            </th>
          </tr>
        </thead>
        <tbody>
          {tests.map((t, i) => (
            <tr key={i} className="border-b border-gray-100 last:border-0">
              <td className="py-2 pr-3 font-medium text-gray-900">
                {t.muscleGroup}
              </td>
              <td className="py-2 px-2 text-center text-gray-600 capitalize">
                {t.side || "-"}
              </td>
              <td className="py-2 pl-2 text-right font-mono font-semibold text-gray-900">
                {t.grade !== undefined ? `${t.grade}/5` : "-"}
                {t.gradeLabel && (
                  <span className="ml-1 text-xs font-normal text-gray-500">
                    ({t.gradeLabel})
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── Main SOAP Editor ────────────────────────────────────────

export function SOAPNoteEditor({
  note,
  onChange,
  readOnly = false,
}: SOAPNoteEditorProps) {
  const updateSubjective = useCallback(
    (patch: Partial<Subjective>) => {
      onChange?.({ ...note, subjective: { ...note.subjective, ...patch } });
    },
    [note, onChange]
  );

  const updateObjective = useCallback(
    (patch: Partial<Objective>) => {
      onChange?.({ ...note, objective: { ...note.objective, ...patch } });
    },
    [note, onChange]
  );

  const updateAssessment = useCallback(
    (patch: Partial<Assessment>) => {
      onChange?.({ ...note, assessment: { ...note.assessment, ...patch } });
    },
    [note, onChange]
  );

  const updatePlan = useCallback(
    (patch: Partial<Plan>) => {
      onChange?.({ ...note, plan: { ...note.plan, ...patch } });
    },
    [note, onChange]
  );

  const s = note.subjective;
  const o = note.objective;
  const a = note.assessment;
  const p = note.plan;

  return (
    <div className="space-y-3">
      {/* ── SUBJECTIVE ────────────────────────────────────── */}
      <CollapsibleCard
        title="Subjective"
        icon={<MessageSquare className="h-4 w-4" />}
        defaultOpen
      >
        <dl className="space-y-4">
          <EditableField
            label="Chief Complaint"
            value={s?.chiefComplaint}
            onSave={(v) => updateSubjective({ chiefComplaint: v })}
            readOnly={readOnly}
            multiline
          />
          <EditableField
            label="Patient Reported Symptoms"
            value={s?.patientReportedSymptoms}
            onSave={(v) => updateSubjective({ patientReportedSymptoms: v })}
            readOnly={readOnly}
            multiline
          />
          <div className="grid grid-cols-2 gap-4">
            <EditableField
              label="Pain Location"
              value={s?.painLocation}
              onSave={(v) => updateSubjective({ painLocation: v })}
              readOnly={readOnly}
            />
            <EditableField
              label="Pain Scale (0-10)"
              value={s?.painScale}
              onSave={(v) =>
                updateSubjective({
                  painScale: v ? parseInt(v) : undefined,
                })
              }
              readOnly={readOnly}
              type="number"
            />
          </div>
          <EditableField
            label="Pain Quality"
            value={s?.painQuality}
            onSave={(v) => updateSubjective({ painQuality: v })}
            readOnly={readOnly}
          />
          <EditableField
            label="Aggravating Factors"
            value={s?.aggravatingFactors}
            onSave={(v) => updateSubjective({ aggravatingFactors: v })}
            readOnly={readOnly}
            multiline
          />
          <EditableField
            label="Relieving Factors"
            value={s?.relievingFactors}
            onSave={(v) => updateSubjective({ relievingFactors: v })}
            readOnly={readOnly}
            multiline
          />
          <EditableField
            label="Prior Level of Function"
            value={s?.priorLevelOfFunction}
            onSave={(v) => updateSubjective({ priorLevelOfFunction: v })}
            readOnly={readOnly}
            multiline
          />
          <EditableField
            label="Patient Goals"
            value={s?.patientGoals}
            onSave={(v) => updateSubjective({ patientGoals: v })}
            readOnly={readOnly}
            multiline
          />
          <EditableField
            label="Medical History"
            value={s?.medicalHistory}
            onSave={(v) => updateSubjective({ medicalHistory: v })}
            readOnly={readOnly}
            multiline
          />
          <EditableField
            label="Current Medications"
            value={s?.currentMedications}
            onSave={(v) => updateSubjective({ currentMedications: v })}
            readOnly={readOnly}
            multiline
          />
          <EditableField
            label="Precautions / Contraindications"
            value={s?.precautions}
            onSave={(v) => updateSubjective({ precautions: v })}
            readOnly={readOnly}
            multiline
          />
        </dl>
      </CollapsibleCard>

      {/* ── OBJECTIVE ─────────────────────────────────────── */}
      <CollapsibleCard
        title="Objective"
        icon={<Activity className="h-4 w-4" />}
        defaultOpen
      >
        <div className="space-y-5">
          <div>
            <h4 className="mb-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Vital Signs
            </h4>
            <VitalSignsSection
              vitals={o?.vitalSigns}
              onChange={(v) => updateObjective({ vitalSigns: v })}
              readOnly={readOnly}
            />
          </div>

          <dl className="space-y-4">
            <EditableField
              label="Observation / General Appearance"
              value={o?.observation}
              onSave={(v) => updateObjective({ observation: v })}
              readOnly={readOnly}
              multiline
            />
            <EditableField
              label="Posture"
              value={o?.posture}
              onSave={(v) => updateObjective({ posture: v })}
              readOnly={readOnly}
              multiline
            />
            <EditableField
              label="Gait"
              value={o?.gait}
              onSave={(v) => updateObjective({ gait: v })}
              readOnly={readOnly}
              multiline
            />
            <EditableField
              label="Palpation"
              value={o?.palpation}
              onSave={(v) => updateObjective({ palpation: v })}
              readOnly={readOnly}
              multiline
            />
            <EditableField
              label="Special Tests"
              value={o?.specialTests}
              onSave={(v) => updateObjective({ specialTests: v })}
              readOnly={readOnly}
              multiline
            />
            <EditableField
              label="Neurovascular Status"
              value={o?.neurovascularStatus}
              onSave={(v) => updateObjective({ neurovascularStatus: v })}
              readOnly={readOnly}
              multiline
            />
            <EditableField
              label="Edema"
              value={o?.edema}
              onSave={(v) => updateObjective({ edema: v })}
              readOnly={readOnly}
            />
          </dl>

          <div>
            <h4 className="mb-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Range of Motion
            </h4>
            <ROMTable
              measurements={o?.romMeasurements}
              onChange={(v) => updateObjective({ romMeasurements: v })}
              readOnly={readOnly}
            />
          </div>

          <div>
            <h4 className="mb-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Strength Testing
            </h4>
            <StrengthTable tests={o?.strengthTests} readOnly={readOnly} />
          </div>

          {o?.functionalAssessment && (
            <dl className="space-y-4">
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Functional Assessment
              </h4>
              <EditableField
                label="Transfers"
                value={o.functionalAssessment.transfers}
                onSave={(v) =>
                  updateObjective({
                    functionalAssessment: {
                      ...o.functionalAssessment,
                      transfers: v,
                    },
                  })
                }
                readOnly={readOnly}
                multiline
              />
              <EditableField
                label="Ambulation"
                value={o.functionalAssessment.ambulation}
                onSave={(v) =>
                  updateObjective({
                    functionalAssessment: {
                      ...o.functionalAssessment,
                      ambulation: v,
                    },
                  })
                }
                readOnly={readOnly}
                multiline
              />
              <EditableField
                label="Balance"
                value={o.functionalAssessment.balance}
                onSave={(v) =>
                  updateObjective({
                    functionalAssessment: {
                      ...o.functionalAssessment,
                      balance: v,
                    },
                  })
                }
                readOnly={readOnly}
                multiline
              />
              <EditableField
                label="ADLs"
                value={o.functionalAssessment.adls}
                onSave={(v) =>
                  updateObjective({
                    functionalAssessment: {
                      ...o.functionalAssessment,
                      adls: v,
                    },
                  })
                }
                readOnly={readOnly}
                multiline
              />
              <EditableField
                label="Fall Risk"
                value={o.functionalAssessment.fallRisk}
                onSave={(v) =>
                  updateObjective({
                    functionalAssessment: {
                      ...o.functionalAssessment,
                      fallRisk: v as "low" | "moderate" | "high",
                    },
                  })
                }
                readOnly={readOnly}
              />
              <EditableField
                label="Weight Bearing Status"
                value={o.functionalAssessment.weightBearingStatus}
                onSave={(v) =>
                  updateObjective({
                    functionalAssessment: {
                      ...o.functionalAssessment,
                      weightBearingStatus: v,
                    },
                  })
                }
                readOnly={readOnly}
              />
            </dl>
          )}
        </div>
      </CollapsibleCard>

      {/* ── ASSESSMENT ────────────────────────────────────── */}
      <CollapsibleCard
        title="Assessment"
        icon={<Brain className="h-4 w-4" />}
        defaultOpen
      >
        <dl className="space-y-4">
          <EditableField
            label="Diagnosis"
            value={a?.diagnosis}
            onSave={(v) => updateAssessment({ diagnosis: v })}
            readOnly={readOnly}
            multiline
          />
          <EditableField
            label="Clinical Impression"
            value={a?.clinicalImpression}
            onSave={(v) => updateAssessment({ clinicalImpression: v })}
            readOnly={readOnly}
            multiline
          />
          <EditableField
            label="Functional Limitations"
            value={a?.functionalLimitations}
            onSave={(v) => updateAssessment({ functionalLimitations: v })}
            readOnly={readOnly}
            multiline
          />
          <EditableField
            label="Rehabilitation Potential"
            value={a?.rehabilitationPotential}
            onSave={(v) =>
              updateAssessment({
                rehabilitationPotential: v as Assessment["rehabilitationPotential"],
              })
            }
            readOnly={readOnly}
          />
          <EditableField
            label="Goals Status"
            value={a?.goalsStatus}
            onSave={(v) => updateAssessment({ goalsStatus: v })}
            readOnly={readOnly}
            multiline
          />
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
              Short-Term Goals
            </p>
            {a?.shortTermGoals?.length ? (
              <ul className="space-y-1">
                {a.shortTermGoals.map((goal, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-900">
                    <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-brand-400 shrink-0" />
                    {goal}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-gray-400 italic">
                {readOnly ? "Not documented" : "No short-term goals added"}
              </p>
            )}
          </div>
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
              Long-Term Goals
            </p>
            {a?.longTermGoals?.length ? (
              <ul className="space-y-1">
                {a.longTermGoals.map((goal, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-900">
                    <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-medical-green shrink-0" />
                    {goal}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-gray-400 italic">
                {readOnly ? "Not documented" : "No long-term goals added"}
              </p>
            )}
          </div>
          {a?.icdCodes?.length && (
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
                ICD-10 Codes
              </p>
              <div className="flex flex-wrap gap-1.5">
                {a.icdCodes.map((code, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center rounded-md bg-gray-100 px-2.5 py-1 text-xs font-mono font-medium text-gray-700"
                  >
                    {code}
                  </span>
                ))}
              </div>
            </div>
          )}
        </dl>
      </CollapsibleCard>

      {/* ── PLAN ──────────────────────────────────────────── */}
      <CollapsibleCard
        title="Plan"
        icon={<ClipboardList className="h-4 w-4" />}
        defaultOpen
      >
        <dl className="space-y-4">
          <EditableField
            label="Treatment Provided"
            value={p?.treatmentProvided}
            onSave={(v) => updatePlan({ treatmentProvided: v })}
            readOnly={readOnly}
            multiline
          />
          {p?.treatmentTechniques?.length && (
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
                Treatment Techniques
              </p>
              <ul className="space-y-1">
                {p.treatmentTechniques.map((t, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-2 text-sm text-gray-900"
                  >
                    <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-brand-400 shrink-0" />
                    {t}
                  </li>
                ))}
              </ul>
            </div>
          )}
          <EditableField
            label="Home Exercise Program"
            value={p?.homeExerciseProgram}
            onSave={(v) => updatePlan({ homeExerciseProgram: v })}
            readOnly={readOnly}
            multiline
          />
          <EditableField
            label="Patient Education"
            value={p?.patientEducation}
            onSave={(v) => updatePlan({ patientEducation: v })}
            readOnly={readOnly}
            multiline
          />
          <EditableField
            label="Frequency / Duration"
            value={p?.frequencyDuration}
            onSave={(v) => updatePlan({ frequencyDuration: v })}
            readOnly={readOnly}
          />
          <EditableField
            label="Next Visit Plan"
            value={p?.nextVisitPlan}
            onSave={(v) => updatePlan({ nextVisitPlan: v })}
            readOnly={readOnly}
            multiline
          />
          <EditableField
            label="Additional Notes"
            value={p?.additionalNotes}
            onSave={(v) => updatePlan({ additionalNotes: v })}
            readOnly={readOnly}
            multiline
          />
        </dl>
      </CollapsibleCard>
    </div>
  );
}
