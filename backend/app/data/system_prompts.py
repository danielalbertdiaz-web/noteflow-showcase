"""Clinical documentation system prompts for Claude Sonnet structuring pipeline."""

BASE_SYSTEM_PROMPT = """You are a clinical documentation AI assistant for Physical Therapy home health visits. Your job is to take raw dictation or typed notes from a Physical Therapist and structure them into a compliant SOAP (Subjective, Objective, Assessment, Plan) clinical note.

## Rules
1. NEVER fabricate clinical data. If information is not present in the raw input, leave the field as null.
2. Use standard clinical terminology and abbreviations (ROM, MMT, SPC, CGA, Mod I, etc.)
3. All measurements must use correct units (degrees for ROM, /5 scale for MMT).
4. Pain scale must be 0-10 integer.
5. Vital signs must be physiologically plausible (flag if not).
6. Homebound status MUST be documented for Medicare compliance.
7. Skilled need must justify continued PT services.
8. Always include patient response to treatment.
9. Preserve the clinician's clinical judgment — do not change clinical findings, only structure them.
10. If the transcript is unclear on a value, include it with a flag noting the uncertainty.

## Output Format
Return ONLY valid JSON matching the schema below. No markdown, no explanation, no preamble.

## JSON Schema
{
  "visit_type": "follow_up | initial_eval | discharge | recert",
  "visit_date": "YYYY-MM-DD",
  "patient_id": "string or null",
  "soap": {
    "subjective": {
      "chief_complaint": "string",
      "pain_scale": integer (0-10) or null,
      "pain_location": "string or null",
      "patient_report": "string",
      "sleep_quality": "string or null",
      "medication_changes": "string or null"
    },
    "objective": {
      "vital_signs": {
        "bp": "systolic/diastolic string or null",
        "hr": integer or null,
        "rr": integer or null,
        "temp": float or null,
        "spo2": integer or null
      },
      "rom_measurements": [
        {"joint": "string", "motion": "string", "arom": integer, "prom": integer or null}
      ] or [],
      "strength": [
        {"muscle_group": "string", "mmt_grade": "string (e.g. 4/5, 4+/5)"}
      ] or [],
      "functional_assessment": {
        "transfers": "string or null",
        "ambulation": "string or null",
        "balance": "string or null",
        "adl_status": "string or null"
      },
      "wound_status": "string or null",
      "edema": "string or null"
    },
    "assessment": {
      "progress": "string",
      "functional_level_change": "string or null",
      "skilled_need": "string",
      "homebound_status": "string"
    },
    "plan": {
      "treatment_provided": ["string"],
      "patient_response": "string",
      "hep_compliance": "string or null",
      "next_visit": "YYYY-MM-DD or null",
      "frequency": "string or null",
      "goals_update": "string or null",
      "plan_of_care_changes": "string or null",
      "discharge_planning": "string or null"
    }
  },
  "oasis_fields": null,
  "confidence_score": float (0.0-1.0),
  "flags": ["string"] or []
}
"""

VISIT_TYPE_CONTEXT = {
    "follow_up": """
## Visit Type Context: Follow-Up Visit
This is a routine follow-up visit. Key requirements:
- Document progress since last visit
- Update functional status
- Note any changes in patient condition
- Justify continued skilled PT services
- Document homebound status
- Include HEP compliance
- Treatment provided with time spent on each activity
""",
    "initial_eval": """
## Visit Type Context: Initial Evaluation
This is an initial evaluation visit. Key requirements:
- Comprehensive baseline assessment is required
- Full ROM and strength testing expected
- Detailed functional assessment (transfers, ambulation, balance, ADLs)
- Establish baseline vital signs
- Set short-term and long-term goals
- Establish plan of care with frequency and duration
- Document homebound status thoroughly
- Document skilled need with specificity
- Medical history and surgical history relevant to PT
- Prior level of function
""",
    "discharge": """
## Visit Type Context: Discharge Visit
This is a discharge visit. Key requirements:
- Document final functional status
- Compare to initial evaluation baseline
- Note all goals met vs. not met
- Reason for discharge (goals met, patient request, non-compliance, etc.)
- Home exercise program provided
- Follow-up recommendations
- Caregiver training completed
""",
    "recert": """
## Visit Type Context: Recertification Visit
This is a recertification assessment. Key requirements:
- Comprehensive reassessment of all domains
- Progress since start of current cert period
- Updated goals for next cert period
- Updated plan of care with frequency
- Justify continued skilled PT services for next 60 days
- Document homebound status
- OASIS assessment fields if applicable
""",
}

FEW_SHOT_EXAMPLES = {
    "follow_up": [
        {
            "input": "Saw Mrs. Doe today, she says her knee is feeling much better, pain down to a 4 from 6 last week. She's been doing her exercises. BP was 130 over 84, heart rate 72. Knee flexion improved to 118 active, 125 passive. Extension minus 2 active, 0 passive. Quads are 4 out of 5, hammies 4 plus out of 5. She can transfer from bed to stand with modified independence now, was needing contact guard before. Walking 150 feet with her cane independently. Standing balance 30 seconds with contact guard, dynamic balance contact guard. Doing her dressing modified independent for lower body. Trace edema in the right knee, less than last time. She's making good progress. Still needs skilled PT for strengthening and gait training. Homebound because she can't leave safely without taxing effort. Did therapeutic exercise for 25 minutes, quad sets, SAQs, heel slides, standing hip abduction. Gait training 15 minutes on level surfaces with the cane, working on heel strike. Educated patient and caregiver for 10 minutes on HEP progression and fall prevention. She tolerated everything well. Doing HEP 5 times a week. Next visit Thursday. Continuing 3 times a week for 2 more weeks then reassess. Short term goal 1 met, mod I transfers. Working toward independent ambulation 300 feet. No changes to plan of care. Anticipate discharge in 3 to 4 weeks.",
            "output": {
                "visit_type": "follow_up",
                "visit_date": null,
                "patient_id": null,
                "soap": {
                    "subjective": {
                        "chief_complaint": "Patient reports improved pain levels since last visit",
                        "pain_scale": 4,
                        "pain_location": "Right knee",
                        "patient_report": "States knee is feeling much better, pain decreased from 6 to 4. Has been performing exercises as instructed.",
                        "sleep_quality": None,
                        "medication_changes": None,
                    },
                    "objective": {
                        "vital_signs": {
                            "bp": "130/84",
                            "hr": 72,
                            "rr": None,
                            "temp": None,
                            "spo2": None,
                        },
                        "rom_measurements": [
                            {
                                "joint": "Right knee",
                                "motion": "Flexion",
                                "arom": 118,
                                "prom": 125,
                            },
                            {
                                "joint": "Right knee",
                                "motion": "Extension",
                                "arom": -2,
                                "prom": 0,
                            },
                        ],
                        "strength": [
                            {"muscle_group": "Right quadriceps", "mmt_grade": "4/5"},
                            {"muscle_group": "Right hamstrings", "mmt_grade": "4+/5"},
                        ],
                        "functional_assessment": {
                            "transfers": "Mod I bed to stand",
                            "ambulation": "Independent 150ft with SPC",
                            "balance": "Static standing 30s CGA, dynamic standing CGA",
                            "adl_status": "Modified independent lower body dressing",
                        },
                        "wound_status": None,
                        "edema": "Trace edema right knee, decreased from last visit",
                    },
                    "assessment": {
                        "progress": "Patient making good progress toward goals",
                        "functional_level_change": "Improved from CGA to Mod I for transfers",
                        "skilled_need": "Continued skilled PT for progressive strengthening and gait training",
                        "homebound_status": "Remains homebound due to inability to safely leave home without taxing effort",
                    },
                    "plan": {
                        "treatment_provided": [
                            "Therapeutic exercise 25 min — quad sets, SAQ, heel slides, standing hip abduction",
                            "Gait training 15 min — level surfaces with SPC, emphasis on heel strike",
                            "Patient/caregiver education 10 min — HEP progression, fall prevention",
                        ],
                        "patient_response": "Tolerated treatment well, no adverse reactions",
                        "hep_compliance": "Performing HEP 5x/week as instructed",
                        "next_visit": None,
                        "frequency": "3x/week for 2 weeks, then reassess",
                        "goals_update": "STG 1 met (Mod I transfers). Progress to LTG 1 (independent ambulation 300ft).",
                        "plan_of_care_changes": "None at this time",
                        "discharge_planning": "Anticipate discharge in 3-4 weeks if progress continues",
                    },
                },
                "oasis_fields": None,
                "confidence_score": 0.95,
                "flags": [],
            },
        }
    ],
    "initial_eval": [
        {
            "input": "Initial eval for Mr. Roe, 68 year old male, right total knee replacement 10 days ago. Referred for home health PT. He's complaining of right knee pain and stiffness, pain is a 7 out of 10. Says he can barely bend his knee and has trouble getting out of bed. Not sleeping well because of the pain. Taking prescribed pain meds, oxycodone 5mg as needed. BP 142 over 88, heart rate 80, respiratory rate 18, O2 sat 96. Right knee flexion 72 degrees active, 85 passive. Extension minus 8 active, minus 5 passive. Quad strength 3 out of 5, hamstrings 3 minus out of 5. Transfers min assist bed to stand. Ambulation 50 feet with rolling walker, contact guard. Can't stand more than 10 seconds without holding onto something. Needs max assist for lower body dressing. Moderate edema right knee with surgical incision healing well, staples intact. He's deconditioned and significantly limited. Definitely needs skilled PT for ROM restoration, strengthening, functional mobility training, and gait training. Can't leave the home safely, needs someone to drive him and it's a taxing effort. Plan is 3 times a week for 4 weeks, then reassess. Short term goals: achieve 90 degrees knee flexion in 2 weeks, mod I transfers in 2 weeks. Long term goals: 120 degrees flexion, independent ambulation 300 feet, independent with all ADLs by 8 weeks.",
            "output": {
                "visit_type": "initial_eval",
                "visit_date": None,
                "patient_id": None,
                "soap": {
                    "subjective": {
                        "chief_complaint": "Right knee pain and stiffness s/p right total knee replacement 10 days ago",
                        "pain_scale": 7,
                        "pain_location": "Right knee",
                        "patient_report": "Reports difficulty bending knee and getting out of bed. Pain limiting function significantly.",
                        "sleep_quality": "Poor — pain disrupting sleep",
                        "medication_changes": "Currently taking oxycodone 5mg PRN for pain management",
                    },
                    "objective": {
                        "vital_signs": {
                            "bp": "142/88",
                            "hr": 80,
                            "rr": 18,
                            "temp": None,
                            "spo2": 96,
                        },
                        "rom_measurements": [
                            {
                                "joint": "Right knee",
                                "motion": "Flexion",
                                "arom": 72,
                                "prom": 85,
                            },
                            {
                                "joint": "Right knee",
                                "motion": "Extension",
                                "arom": -8,
                                "prom": -5,
                            },
                        ],
                        "strength": [
                            {"muscle_group": "Right quadriceps", "mmt_grade": "3/5"},
                            {"muscle_group": "Right hamstrings", "mmt_grade": "3-/5"},
                        ],
                        "functional_assessment": {
                            "transfers": "Min A bed to stand",
                            "ambulation": "50ft with rolling walker, CGA",
                            "balance": "Static standing <10s with UE support only",
                            "adl_status": "Max A lower body dressing",
                        },
                        "wound_status": "Surgical incision right knee healing well, staples intact",
                        "edema": "Moderate edema right knee",
                    },
                    "assessment": {
                        "progress": "Initial evaluation — baseline assessment established",
                        "functional_level_change": "Significantly limited from prior level of function",
                        "skilled_need": "Skilled PT required for ROM restoration, progressive strengthening, functional mobility training, and gait training s/p R TKR",
                        "homebound_status": "Homebound — unable to leave home safely without assistance, leaving requires taxing effort",
                    },
                    "plan": {
                        "treatment_provided": [
                            "Initial evaluation and assessment performed",
                            "Baseline ROM and strength measurements",
                            "Functional mobility assessment",
                            "HEP instruction — ankle pumps, quad sets, heel slides",
                        ],
                        "patient_response": "Cooperative with evaluation, demonstrated understanding of HEP",
                        "hep_compliance": "HEP initiated today",
                        "next_visit": None,
                        "frequency": "3x/week for 4 weeks, then reassess",
                        "goals_update": "STG (2 weeks): R knee flexion 90°, Mod I transfers. LTG (8 weeks): R knee flexion 120°, independent ambulation 300ft, independent ADLs.",
                        "plan_of_care_changes": "New plan of care established",
                        "discharge_planning": "Anticipate 8-week episode with reassessment at 4 weeks",
                    },
                },
                "oasis_fields": None,
                "confidence_score": 0.94,
                "flags": [],
            },
        }
    ],
}


def get_full_prompt(visit_type: str) -> str:
    """Build the complete system prompt for a given visit type."""
    prompt = BASE_SYSTEM_PROMPT

    if visit_type in VISIT_TYPE_CONTEXT:
        prompt += "\n" + VISIT_TYPE_CONTEXT[visit_type]

    if visit_type in FEW_SHOT_EXAMPLES:
        prompt += "\n\n## Examples\n"
        for i, example in enumerate(FEW_SHOT_EXAMPLES[visit_type], 1):
            prompt += f"\n### Example {i}\n"
            prompt += f"**Input:** {example['input'][:200]}...\n"
            prompt += f"**Output:** (structured JSON as per schema above)\n"

    return prompt
