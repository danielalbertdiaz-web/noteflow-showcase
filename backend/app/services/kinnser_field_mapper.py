"""
kinnser_field_mapper.py

Maps NoteFlow structured SOAP note fields to WellSky/Kinnser form field
identifiers, mirroring the label-based detection patterns used by the
Playwright browser-automation worker.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional
import re


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class KinnserFieldMapping:
    """Describes how a single NoteFlow SOAP path maps to a WellSky/Kinnser field."""

    soap_path: str
    """Dotted path into the structured note dict, e.g. 'objective.vitalSigns.heartRate'."""

    field_name: str
    """Human-readable name for the field."""

    selectors: list[str] = field(default_factory=list)
    """CSS selector hints that content.js uses to locate the element."""

    label_search: Optional[str] = None
    """Visible label text that content.js searches for (substring match)."""

    label_strategy: Optional[str] = None
    """Named detection strategy used by content.js for complex label patterns."""

    field_type: str = "text"
    """One of: text, select, checkbox, textarea, auto."""

    transform: Optional[Callable[[Any], Any]] = None
    """Optional callable applied to the extracted value before returning."""


# ---------------------------------------------------------------------------
# Mapping table
# ---------------------------------------------------------------------------

def _bp_split_systolic(value: Any) -> Optional[str]:
    """Extract systolic from a 'systolic/diastolic' string or dict."""
    if isinstance(value, dict):
        return str(value.get("systolic", ""))
    if isinstance(value, str) and "/" in value:
        return value.split("/")[0].strip()
    return str(value) if value is not None else None


def _bp_split_diastolic(value: Any) -> Optional[str]:
    """Extract diastolic from a 'systolic/diastolic' string or dict."""
    if isinstance(value, dict):
        return str(value.get("diastolic", ""))
    if isinstance(value, str) and "/" in value:
        return value.split("/")[1].strip()
    return str(value) if value is not None else None


def _pain_to_bool(value: Any) -> bool:
    """Return True when pain scale is 0 or explicitly None/absent."""
    if value is None:
        return True
    try:
        return int(value) == 0
    except (ValueError, TypeError):
        return False


def _bool_from_list(keyword: str) -> Callable[[Any], bool]:
    """Return a transform that checks whether *keyword* appears in a list field."""
    def _transform(value: Any) -> bool:
        if isinstance(value, list):
            return any(keyword.lower() in str(item).lower() for item in value)
        if isinstance(value, str):
            return keyword.lower() in value.lower()
        return False
    return _transform


KINNSER_FIELD_MAPPINGS: list[KinnserFieldMapping] = [

    # -----------------------------------------------------------------------
    # Visit Info
    # -----------------------------------------------------------------------
    KinnserFieldMapping(
        soap_path="visitDate",
        field_name="Visit Date",
        selectors=["input[name*='visit_date']", "input[name*='VisitDate']"],
        label_search="Visit Date",
        field_type="text",
    ),
    KinnserFieldMapping(
        soap_path="timeIn",
        field_name="Time In",
        selectors=[
            "input[name*='time_in']",
            "input[name*='TimeIn']",
            "input[name*='StartTime']",
        ],
        label_search="Time In",
        field_type="text",
    ),
    KinnserFieldMapping(
        soap_path="timeOut",
        field_name="Time Out",
        selectors=[
            "input[name*='time_out']",
            "input[name*='TimeOut']",
            "input[name*='EndTime']",
        ],
        label_search="Time Out",
        field_type="text",
    ),

    # -----------------------------------------------------------------------
    # Vitals
    # -----------------------------------------------------------------------
    KinnserFieldMapping(
        soap_path="objective.vitalSigns.temperature",
        field_name="Temperature",
        selectors=["input[name*='temp']"],
        label_search="Temperature",
        field_type="text",
    ),
    KinnserFieldMapping(
        soap_path="objective.vitalSigns.temperatureMethod",
        field_name="Temperature Method",
        selectors=["select[name*='temp']"],
        label_search="taken",
        field_type="select",
    ),
    KinnserFieldMapping(
        soap_path="objective.vitalSigns.bloodPressure",
        field_name="BP Systolic (Prior)",
        selectors=[],
        label_search=None,
        label_strategy="bp-systolic-prior",
        field_type="text",
        transform=_bp_split_systolic,
    ),
    KinnserFieldMapping(
        soap_path="objective.vitalSigns.bloodPressure",
        field_name="BP Diastolic (Prior)",
        selectors=[],
        label_search=None,
        label_strategy="bp-diastolic-prior",
        field_type="text",
        transform=_bp_split_diastolic,
    ),
    KinnserFieldMapping(
        soap_path="objective.vitalSigns.bpPosition",
        field_name="BP Position",
        selectors=[],
        label_search=None,
        label_strategy="bp-position",
        field_type="select",
    ),
    KinnserFieldMapping(
        soap_path="objective.vitalSigns.bpSide",
        field_name="BP Side",
        selectors=[],
        label_search=None,
        label_strategy="bp-side",
        field_type="select",
    ),
    KinnserFieldMapping(
        soap_path="objective.vitalSigns.heartRate",
        field_name="Heart Rate",
        selectors=["input[name*='heart_rate']", "input[name*='pulse']"],
        label_search="Heart Rate",
        field_type="text",
    ),
    KinnserFieldMapping(
        soap_path="objective.vitalSigns.respiratoryRate",
        field_name="Respirations",
        selectors=["input[name*='resp']"],
        label_search="Respirations",
        field_type="text",
    ),
    KinnserFieldMapping(
        soap_path="objective.vitalSigns.oxygenSaturation",
        field_name="O2 Sat",
        selectors=["input[name*='o2']", "input[name*='spo2']"],
        label_search="O2 Sat",
        field_type="text",
    ),

    # -----------------------------------------------------------------------
    # Pain
    # -----------------------------------------------------------------------
    KinnserFieldMapping(
        soap_path="objective.vitalSigns.painScale",
        field_name="No Pain Reported",
        selectors=[],
        label_search="No Pain Reported",
        field_type="checkbox",
        transform=_pain_to_bool,
    ),
    KinnserFieldMapping(
        soap_path="subjective.painLocation",
        field_name="Pain Location (Dropdown)",
        selectors=["select"],
        label_search="Location",
        label_strategy="pain-location-primary",
        field_type="select",
    ),
    KinnserFieldMapping(
        soap_path="subjective.painLocation",
        field_name="Pain Location (Text)",
        selectors=[],
        label_search=None,
        label_strategy="pain-location-text-primary",
        field_type="text",
    ),
    KinnserFieldMapping(
        soap_path="subjective.painScale",
        field_name="Pain Pre-Therapy",
        selectors=["select"],
        label_search="Pre-Therapy",
        field_type="select",
        transform=lambda v: str(v) if v is not None else None,
    ),
    KinnserFieldMapping(
        soap_path="objective.vitalSigns.painScale",
        field_name="Pain Post-Therapy",
        selectors=["select"],
        label_search="Post-Therapy",
        field_type="select",
        transform=lambda v: str(v) if v is not None else None,
    ),
    KinnserFieldMapping(
        soap_path="subjective.aggravatingFactors",
        field_name="Pain Increased By",
        selectors=[],
        label_search="Increased by",
        field_type="text",
    ),
    KinnserFieldMapping(
        soap_path="subjective.relievingFactors",
        field_name="Pain Relieved By",
        selectors=[],
        label_search="Relieved by",
        field_type="text",
    ),
    KinnserFieldMapping(
        soap_path="subjective.painBehavior",
        field_name="Pain Interferes With",
        selectors=[],
        label_search="Interferes with",
        field_type="text",
    ),

    # -----------------------------------------------------------------------
    # Subjective
    # -----------------------------------------------------------------------
    KinnserFieldMapping(
        soap_path="subjective.patientReportedSymptoms",
        field_name="Subjective Information Collected During Visit",
        selectors=["textarea"],
        label_search="Subjective Information Collected During Visit",
        field_type="textarea",
    ),

    # -----------------------------------------------------------------------
    # Progress to Goals
    # -----------------------------------------------------------------------
    KinnserFieldMapping(
        soap_path="assessment.goalsStatus",
        field_name="Progress to Goals Indicated By",
        selectors=[],
        label_search="Progress to goals indicated by",
        field_type="text",
    ),
    KinnserFieldMapping(
        soap_path="assessment.clinicalImpression",
        field_name="Needs Continued Skilled PT",
        selectors=[],
        label_search="Needs continued skilled PT to address",
        field_type="text",
    ),
    KinnserFieldMapping(
        soap_path="assessment.prognosticFactors",
        field_name="Progress Delayed Due To",
        selectors=[],
        label_search="Progress delayed due to",
        field_type="text",
    ),

    # -----------------------------------------------------------------------
    # Performance Summary
    # -----------------------------------------------------------------------
    KinnserFieldMapping(
        soap_path="assessment.functionalLimitations",
        field_name="Summary of Patient Overall Performance",
        selectors=["textarea"],
        label_search="Summary of Patient Overall Performance",
        field_type="textarea",
    ),

    # -----------------------------------------------------------------------
    # Plan
    # -----------------------------------------------------------------------
    KinnserFieldMapping(
        soap_path="plan.nextVisitPlan",
        field_name="Plan for Next Visit",
        selectors=[],
        label_search="Plan for next visit",
        field_type="checkbox",
        transform=lambda v: bool(v),
    ),
    KinnserFieldMapping(
        soap_path="plan.additionalNotes",
        field_name="Plan",
        selectors=["textarea"],
        label_search="Plan",
        field_type="textarea",
    ),

    # -----------------------------------------------------------------------
    # Teaching checkboxes
    # -----------------------------------------------------------------------
    KinnserFieldMapping(
        soap_path="plan.homeExerciseProgram",
        field_name="Teaching: Home Exercise Program",
        selectors=[],
        label_search="Home Exercise Program",
        field_type="checkbox",
        transform=lambda v: bool(v),
    ),
    KinnserFieldMapping(
        soap_path="plan.patientEducation",
        field_name="Teaching: Safe Transfer",
        selectors=[],
        label_search="Safe Transfer",
        field_type="checkbox",
        transform=_bool_from_list("safe transfer"),
    ),
    KinnserFieldMapping(
        soap_path="plan.patientEducation",
        field_name="Teaching: Safe Gait",
        selectors=[],
        label_search="Safe Gait",
        field_type="checkbox",
        transform=_bool_from_list("safe gait"),
    ),
    KinnserFieldMapping(
        soap_path="plan.patientEducation",
        field_name="Teaching: Fall Prevention",
        selectors=[],
        label_search="Fall Prevention",
        field_type="checkbox",
        transform=_bool_from_list("fall prevention"),
    ),

    # -----------------------------------------------------------------------
    # Gait Training
    # -----------------------------------------------------------------------
    KinnserFieldMapping(
        soap_path="objective.functionalAssessment.ambulation",
        field_name="Gait Training Distance",
        selectors=[],
        label_search="Distance",
        field_type="text",
    ),
    KinnserFieldMapping(
        soap_path="objective.functionalAssessment.mobilityDevice",
        field_name="Gait Training Device",
        selectors=["select"],
        label_search="Device",
        field_type="select",
    ),
    KinnserFieldMapping(
        soap_path="objective.functionalAssessment.balance",
        field_name="Gait Training Assist Level",
        selectors=["select"],
        label_search="Assist Level",
        field_type="select",
    ),

    # -----------------------------------------------------------------------
    # Discharge Planning
    # -----------------------------------------------------------------------
    KinnserFieldMapping(
        soap_path="plan.frequencyDuration",
        field_name="Discharge Planning",
        selectors=["textarea"],
        label_search="Discharge Planning",
        field_type="textarea",
    ),
]


# ---------------------------------------------------------------------------
# Exercise mappings are generated dynamically (up to 8 slots)
# ---------------------------------------------------------------------------

def _exercise_mappings(count: int = 8) -> list[KinnserFieldMapping]:
    """Generate per-exercise field mappings for slots 1..count."""
    mappings = []
    for i in range(1, count + 1):
        mappings.append(KinnserFieldMapping(
            soap_path=f"exercises[{i - 1}].name",
            field_name=f"Exercise {i} Name",
            selectors=[f"select[name*='exercise_{i}']"],
            field_type="select",
        ))
        mappings.append(KinnserFieldMapping(
            soap_path=f"exercises[{i - 1}].position",
            field_name=f"Exercise {i} Position",
            selectors=[f"select[name*='position_{i}']"],
            field_type="select",
        ))
        mappings.append(KinnserFieldMapping(
            soap_path=f"exercises[{i - 1}].reps",
            field_name=f"Exercise {i} Reps",
            selectors=[f"input[name*='reps_{i}']"],
            field_type="text",
        ))
    return mappings


KINNSER_FIELD_MAPPINGS.extend(_exercise_mappings())


# ---------------------------------------------------------------------------
# Path resolution helpers
# ---------------------------------------------------------------------------

_ARRAY_INDEX_RE = re.compile(r"^(.+)\[(\d+)\]$")


def _get_nested(data: dict, dotted_path: str) -> Any:
    """
    Navigate *data* using a dotted path that may contain array indices.

    Examples::

        _get_nested(note, "objective.vitalSigns.heartRate")
        _get_nested(note, "exercises[0].name")
    """
    parts = dotted_path.split(".")
    current: Any = data
    for part in parts:
        if current is None:
            return None
        m = _ARRAY_INDEX_RE.match(part)
        if m:
            key, idx = m.group(1), int(m.group(2))
            if isinstance(current, dict):
                current = current.get(key)
            else:
                return None
            if not isinstance(current, (list, tuple)) or idx >= len(current):
                return None
            current = current[idx]
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def map_soap_to_kinnser_fields(structured_note: dict) -> list[dict]:
    """
    Convert a NoteFlow structured SOAP note to a list of field descriptors
    ready for the Playwright autofill layer.

    Parameters
    ----------
    structured_note:
        NoteFlow SOAPNote dict (see module docstring for schema).

    Returns
    -------
    list of dicts, each with keys:
        field_name      – human-readable label
        selectors       – list of CSS selector strings
        label_search    – visible label text to locate the element (or None)
        label_strategy  – named strategy for complex patterns (or None)
        field_type      – "text" | "select" | "checkbox" | "textarea" | "auto"
        value           – extracted (and optionally transformed) value
    """
    results: list[dict] = []

    for mapping in KINNSER_FIELD_MAPPINGS:
        raw_value = _get_nested(structured_note, mapping.soap_path)

        # Apply transform if provided
        if mapping.transform is not None:
            try:
                value = mapping.transform(raw_value)
            except Exception:
                value = raw_value
        else:
            value = raw_value

        # Skip fields that have no useful value (keeps the payload lean)
        if value is None or value == "":
            continue

        results.append({
            "field_name": mapping.field_name,
            "selectors": list(mapping.selectors),
            "label_search": mapping.label_search,
            "label_strategy": mapping.label_strategy,
            "field_type": mapping.field_type,
            "value": value,
        })

    return results
