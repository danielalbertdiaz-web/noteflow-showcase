"""
LLM-based SOAP note structuring service using Anthropic Claude.
"""

import json
import logging
import re
from typing import Any

import requests as http_requests

from app.core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a clinical documentation specialist AI assistant for home health physical therapy.
Your task is to transform raw dictated or transcribed clinical notes into structured SOAP format.

## Output Requirements
Return ONLY a valid JSON object matching the schema below. No markdown, no prose, no code fences.

## Schema
{
  "subjective": {
    "chief_complaint": "string or null",
    "pain_scale": 0-10 number or null,
    "pain_location": "string or null",
    "pain_quality": "string or null",
    "aggravating_factors": ["list of strings"] or null,
    "relieving_factors": ["list of strings"] or null,
    "patient_goals": ["list of strings"] or null,
    "progress_since_last_visit": "string or null",
    "patient_reported_function": "string or null"
  },
  "objective": {
    "vital_signs": {
      "blood_pressure": "systolic/diastolic string or null",
      "heart_rate": integer bpm or null,
      "respiratory_rate": integer or null,
      "oxygen_saturation": float % or null,
      "temperature": float °F or null,
      "weight": float lbs or null,
      "height": float inches or null
    } or null,
    "rom_measurements": [
      {"joint": "string", "movement": "string", "active_rom": degrees float or null,
       "passive_rom": degrees float or null, "normal_rom": degrees float or null}
    ] or null,
    "strength_tests": [
      {"muscle_group": "string", "grade": 0-5 float, "notes": "string or null"}
    ] or null,
    "functional_assessments": [
      {"activity": "string", "score": number or null, "scale": "FIM/Barthel/etc or null",
       "notes": "string or null"}
    ] or null,
    "observation": "general physical findings string or null",
    "palpation": "string or null",
    "special_tests": {"test_name": "result"} or null
  },
  "assessment": {
    "clinical_impression": "string or null",
    "progress_toward_goals": "string or null",
    "skilled_care_rationale": "string or null",
    "barriers_to_progress": ["list"] or null,
    "rehab_potential": "good|fair|poor|guarded or null",
    "diagnosis_codes": ["ICD-10 codes"] or null
  },
  "plan": {
    "interventions": ["list of therapeutic interventions"] or null,
    "home_exercise_program": ["list of HEP exercises"] or null,
    "frequency": "e.g. 3x/week or null",
    "duration": "e.g. 6 weeks or null",
    "short_term_goals": [{"goal": "string", "timeframe": "string or null",
                          "measurable_outcome": "string or null"}] or null,
    "long_term_goals": [{"goal": "string", "timeframe": "string or null",
                         "measurable_outcome": "string or null"}] or null,
    "patient_education": ["list"] or null,
    "referrals": ["list"] or null,
    "next_visit_date": "YYYY-MM-DD or null"
  },
  "oasis": {
    "m1800_grooming": 0-3 int or null,
    "m1810_dress_upper": 0-3 int or null,
    "m1820_dress_lower": 0-3 int or null,
    "m1830_bathing": 0-6 int or null,
    "m1840_toilet_transferring": 0-5 int or null,
    "m1850_transferring": 0-6 int or null,
    "m1860_ambulation": 0-6 int or null,
    "m2020_management_oral_medications": 0-3 int or null,
    "fall_risk_score": float or null
  } or null,
  "visit_minutes": integer or null,
  "travel_minutes": integer or null,
  "co_treatment": boolean or null,
  "supervision_percent": 0-100 float or null
}

## Clinical Validation Rules
- Pain scale MUST be 0-10. If stated as fraction (e.g., "7 out of 10"), extract the numerator.
- MMT grades MUST be 0-5. Partial grades (e.g., 4+) should be expressed as 4.5.
- ROM values MUST be in degrees. If percentage of normal is given, convert to degrees using standard norms.
- Blood pressure MUST be formatted as "systolic/diastolic" (e.g., "120/80").
- Oxygen saturation MUST be a percentage float between 0 and 100.
- rehab_potential MUST be one of: "good", "fair", "poor", "guarded", or null.
- ICD-10 codes should be in standard format (e.g., "M54.5", "G35").
- OASIS scores MUST be integers within their valid ranges.

## Missing Information
If a field is not mentioned in the note, set it to null. Do not hallucinate clinical values.
If a value seems clinically implausible (e.g., pain scale 15/10, ROM 300 degrees), set it to null
and add a flag in a "confidence_flags" top-level key.

## Shorthand Expansion Examples
PTs frequently write in shorthand. Here are real examples of shorthand input and the expected clinical assessment output:

### Example 1
Input: "Gait training RW cues heel strike posture STS hand placement cues standing balance perturbations fatigue after gait poor carryover"
Expected Assessment: "Patient participated in skilled physical therapy to address impaired balance, decreased transfer efficiency, and gait instability affecting safe functional mobility. Skilled gait training was performed using a rolling walker with verbal and tactile cueing to improve heel strike, posture, and step sequencing. Transfer training focused on sit-to-stand mechanics with cueing for hand placement and weight shift to improve safety and control. Standing balance activities with graded perturbations were performed to improve postural stability and reduce fall risk. Patient demonstrated fatigue following gait activities and required repeated cueing throughout session with limited carryover noted. Continued skilled PT remains indicated to improve mobility, safety awareness, and independence with functional tasks."

### Example 2
Input: "MFR lumbar gait RW cues proximity forward lean posture improved distance today needs reminders"
Expected Assessment: "Patient participated in skilled physical therapy to address postural deficits, gait instability, and decreased functional mobility. Skilled gait training was performed using a rolling walker with verbal cueing to improve walker proximity and upright posture, as patient demonstrated forward trunk lean during ambulation. Manual therapy including myofascial release to the lumbar region was applied to reduce soft tissue restriction and improve trunk mobility for functional activities. Patient demonstrated slight improvement in gait distance compared to prior session but continued to require frequent reminders for proper technique. Continued skilled PT remains necessary to improve posture, gait safety, and mobility tolerance."

### Example 3
Input: "supine LE stretch patella mobs L knee soreness from bike no pain change better movement"
Expected Assessment: "Patient participated in skilled physical therapy to address lower extremity tightness and decreased mobility affecting functional activity tolerance. Skilled stretching to the lower extremities was performed in supine to improve flexibility and joint mobility. Patellar mobilizations were applied to the left knee to improve patellar tracking and reduce movement restriction. Patient reported soreness following prior exercise activity; however, improved movement quality was observed during this session despite no significant change in reported pain levels. Continued skilled PT remains indicated to improve mobility and support functional performance."

### Example 4
Input: "transfer supine to sit mod assist fearful movement standing tolerance low balance deficits"
Expected Assessment: "Patient participated in skilled physical therapy to address impaired balance, decreased transfer ability, and reduced standing tolerance affecting functional mobility. Transfer training from supine to sitting required moderate assistance with skilled cueing to improve sequencing and safety. Patient demonstrated apprehension with movement, requiring reassurance and close guidance throughout session. Standing tolerance remained limited due to balance deficits and decreased confidence. Continued skilled PT is required to improve transfer independence, balance, and safety during mobility tasks."

## Key Style Rules for Assessment Output
1. Always start with "Patient participated in skilled physical therapy to address [problem list]"
2. Each intervention gets a full clinical description with purpose
3. Patient response documented (fatigue, fear, improvement, tolerance)
4. End with "Continued skilled PT remains indicated/necessary/required to improve [goals]"
5. Expand all abbreviations: RW=rolling walker, STS=sit-to-stand, MFR=myofascial release, LE=lower extremity, mobs=mobilizations, mod assist=moderate assistance, CGA=contact guard assist
6. Must demonstrate medical necessity, skilled intervention, and functional limitation (Medicare compliance)

## Visit Type Context
"""

VISIT_TYPE_CONTEXT = {
    "initial_eval": """This is an INITIAL EVALUATION. Focus on:
- Comprehensive baseline ROM and strength measurements
- Functional status at start of care
- Establishing short and long-term goals
- OASIS scoring if home health
- Diagnosis and prognosis
- Full subjective history""",

    "follow_up": """This is a FOLLOW-UP VISIT. Focus on:
- Progress compared to initial eval / previous visit
- Current ROM and strength measurements
- Response to treatment
- Plan modifications if needed
- Goal progression""",

    "discharge": """This is a DISCHARGE NOTE. Focus on:
- Final functional status compared to admission
- Goal achievement
- Discharge instructions and HEP
- Reason for discharge
- Recommendations for continued care if applicable""",

    "recert": """This is a RECERTIFICATION NOTE. Focus on:
- Progress over the certification period
- Justification for continued skilled PT services
- Updated goals for next certification period
- OASIS recertification scoring""",
}


class NoteStructuringService:
    """
    Structures raw clinical text into a validated SOAP JSON object
    using Anthropic Claude claude-sonnet-4-5.
    """

    MODEL = "gemini-2.5-flash"
    MAX_TOKENS = 4096

    async def structure_note(self, raw_text: str, visit_type: str) -> dict[str, Any]:
        """
        Transform *raw_text* into a structured SOAP note dict via Gemini REST API.

        Returns a dict with keys: structured_note (SOAPNote dict),
        confidence_score (float 0-1), flags (list of validation issues).
        """
        import asyncio

        visit_context = VISIT_TYPE_CONTEXT.get(visit_type, "")
        system = SYSTEM_PROMPT + visit_context
        user_msg = f"Structure the following clinical note for a {visit_type.replace('_', ' ')} visit:\n\n{raw_text}"

        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, lambda: self._call_gemini(system, user_msg))

        raw_json_text = response.strip()

        # Strip accidental markdown fences if model adds them
        raw_json_text = re.sub(r"^```(?:json)?\s*", "", raw_json_text)
        raw_json_text = re.sub(r"\s*```$", "", raw_json_text)

        try:
            parsed = json.loads(raw_json_text)
        except json.JSONDecodeError as exc:
            logger.error("LLM returned invalid JSON: %s\nRaw: %s", exc, raw_json_text[:500])
            raise ValueError(f"LLM returned invalid JSON: {exc}") from exc

        # Extract flags and confidence from top-level if present
        flags = parsed.pop("confidence_flags", None)
        structured = {k: v for k, v in parsed.items() if k != "confidence_flags"}

        # Compute a simple confidence score based on field completeness
        confidence_score = self._compute_confidence(structured)

        return {
            "structured_note": structured,
            "confidence_score": confidence_score,
            "flags": flags,
        }

    def _call_gemini(self, system: str, user_msg: str) -> str:
        """Synchronous Gemini REST API call — no event loop conflicts."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.MODEL}:generateContent?key={settings.GOOGLE_AI_API_KEY}"
        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"parts": [{"text": user_msg}]}],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": self.MAX_TOKENS,
            },
        }
        resp = http_requests.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

    def _compute_confidence(self, note: dict[str, Any]) -> float:
        """
        Heuristic confidence score (0.0–1.0) based on how many key
        SOAP fields are populated.
        """
        key_fields = [
            ("subjective", "chief_complaint"),
            ("subjective", "pain_scale"),
            ("objective", "rom_measurements"),
            ("objective", "strength_tests"),
            ("assessment", "clinical_impression"),
            ("assessment", "skilled_care_rationale"),
            ("plan", "interventions"),
            ("plan", "short_term_goals"),
        ]
        filled = sum(
            1
            for section, field in key_fields
            if note.get(section) and note[section].get(field) is not None
        )
        return round(filled / len(key_fields), 2)
