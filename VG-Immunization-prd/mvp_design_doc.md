# Immunization Ledger — Data Schema Design

## Overview
This document defines the schema for sample patient immunization records (Dataset A), which feed into the AI-assisted pipeline that produces the structured immunization ledger.

**Pipeline flow:**
1. Raw dose records (this schema) — sample data, written manually
    - for scaling rely on LLM's to do extractions of PDF's and images and put them into JSON-format. But what does the actual raw database look like- no clue.
    - biggest problem: I need a much bigger dataset to test if extraction is accurate and how expensive these calls will actually be
2. Each `vaccine_name` is mapped to the disease(s) it prevents + formulation type.
    - created vaccine_mapping json
3. Records grouped by disease prevented 
    - write a optimized pipeline for transformation
4. Doses within each group sorted chronologically and labeled (Dose 1, Dose 2, Booster)
5. Completion status computed per disease group
    - need rag; collect state and school vaccine requirements 
6. Output: structured ledger (UI-ready)
7. Feed ledger and dictionaries to AI Chatbox for RAG

---

## Dataset A: Raw Dose Record Schema

Each record represents one administered vaccine dose. 

| Field | Type | Description | Example |
|---|---|---|---|
| `user_id` | string | Unique identifier for this vaccination record | `"user_001"` |
| `patient_name` | string | full name of the patient | `"Daphne Amazing"` |
| `vaccine_name` | string | Vaccine abbreviation/name as it appears on records | `"DTaP-Hib-IPV"` |
| `dose_date` | string (ISO 8601) | Date the dose was administered | `"2018-02-28"` |
| `manufacturer` | string | Vaccine manufacturer | `"Sanofi"` |
| `lot_number` | string | Lot number from the vial | `"A123"` |
| `provider` | string | Administering provider/physician | `"Dr. Smith"` |
| `clinic` | string | Clinic or facility name | `"TEST IMMPRINT CLINIC"` |

### Example Record
```json
{
  "record_id": "rec_001",
  "vaccine_name": "DTaP-Hib-IPV",
  "dose_date": "2018-02-28",
  "manufacturer": "Sanofi",
  "lot_number": "A123",
  "provider": "Dr. Smith",
  "clinic": "TEST IMMPRINT CLINIC"
}
```

---

## The D/d Disease Classification Challenge

Vaccine abbreviations encode **disease + formulation strength** using capitalization. Same letter, different case = different antigen dose, but same disease target.

| Letter | Disease | Capital (Full-strength) | Lowercase (Reduced-strength) |
|---|---|---|---|
| D / d | Diphtheria | **D** — used in pediatric formulations (DTaP, DT) for children under 7 | **d** — used in adolescent/adult formulations (Tdap, Td) |
| P / p | Pertussis | **P** — full-strength (DTaP) | **p** — acellular reduced (Tdap) |
| a | Acellular | `a` prefix (DTaP, Tdap) = acellular pertussis component, vs. whole-cell `w` (DTwP, older/international formulations) |

### Examples of vaccine name variants to include in Dataset A:
- `DTaP` — pediatric, full-strength diphtheria + pertussis
- `Tdap` — adolescent/adult booster, reduced-strength diphtheria + pertussis
- `Td` — adult booster, tetanus + reduced diphtheria, no pertussis
- `DT` — pediatric, used when pertussis component contraindicated

**Goal:** Gemini must correctly classify all of these as preventing **Diphtheria** and/or **Tetanus** and/or **Pertussis**, while recognizing that DTaP (age <7) and Tdap (age 7+) are different formulations of the same disease targets — relevant for dose sequencing and completion logic.

---

## Gemini Classification Output Schema

For each unique `vaccine_name`, Gemini returns:

```json
{
  "vaccine_name": "DTaP",
  "diseases_prevented": ["Diphtheria", "Tetanus", "Pertussis"],
  "formulation": "pediatric_full_strength",
  "typical_age_range": "6 weeks - 6 years",
  "expected_total_doses": 5
}
```

`expected_total_doses` is the number of doses the CDC schedule recommends for this disease/formulation combination by the relevant age — this is what makes completion calculable.

---

## Output Schema: Disease Group Summary (Ledger Entry)

This is the structured output the UI displays — one entry per disease, aggregating all related vaccine doses.

| Field | Type | Description | Example |
|---|---|---|---|
| `disease_name` | string | The disease this group covers | `"Pertussis"` |
| `doses_received` | array | List of administered doses, sorted chronologically, each labeled | see below |
| `doses_completed_count` | int | Number of doses received | `4` |
| `doses_expected_count` | int | Number of doses expected per schedule | `5` |
| `completion_status` | string | `"Complete"`, `"Partial"`, or `"Overdue"` | `"Partial"` |
| `missing_doses` | array | List of missing dose labels, if any | `["Dose 5 (Booster, age 4-6)"]` |

### Example Output Entry
```json
{
  "user_id": "user_001",
  "patient_name": "Daphne Amazing",
  "generated_at": "2026-06-16T22:30:00Z",
  "ledger": [
    {
      "disease_name": "Pertussis",
      "doses_received": [
        {"dose_label": "Dose 1", "vaccine_name": "DTaP-Hib-IPV", "dose_date": "2018-02-28"},
        {"dose_label": "Dose 2", "vaccine_name": "DTaP-Hib-IPV", "dose_date": "2018-04-30"},
        {"dose_label": "Dose 3", "vaccine_name": "DTaP-Hib-IPV", "dose_date": "2018-06-30"},
        {"dose_label": "Dose 4", "vaccine_name": "DTaP-IPV", "dose_date": "2022-12-31"}
      ],
      "doses_completed_count": 4,
      "doses_expected_count": 5,
      "completion_status": "Partial",
      "missing_doses": ["Dose 5 (Booster, age 4-6 years)"]
    },
    {
      "disease_name": "Diphtheria",
      "doses_received": [...],
      "doses_completed_count": 4,
      "doses_expected_count": 5,
      "completion_status": "Partial",
      "missing_doses": ["Dose 5 (Booster, age 4-6 years)"]
    }
  ]
}
```

### Completion Status Logic
#### Currently would only check against federal level requirement(can drill down to more local levels when data is provided)
- **Complete**: `doses_completed_count >= doses_expected_count`
- **Partial**: `doses_completed_count < doses_expected_count` AND patient is younger than the age window for the missing dose (not yet due)
- **Overdue**: `doses_completed_count < doses_expected_count` AND patient has passed the recommended age window for a missing dose

This means `completion_status` depends on **patient age**, which must be part of the patient profile (separate from individual dose records).

---

## Patient Profile (Required for Completion Logic)

| Field | Type | Description | Example |
|---|---|---|---|
| `patient_id` | string | Unique patient identifier | `"pat_001"` |
| `date_of_birth` | string (ISO 8601) | Used to compute current age and determine overdue status | `"2018-01-10"` |
| `state` | string | State of residence — determines which requirements apply | `"AL"` |
| `institution_type` | string | `"school"`, `"childcare"`, `"college"`, etc. — determines applicable requirement set | `"public_school"` |

---

## Open Questions / Next Steps
- [ ] Confirm completion status logic: based on dose count alone, or age-adjusted against CDC schedule (Dataset B)?
- [ ] NEED DATA for input and LLM Decisions on vaccine completion
- [ ] Define "Dose 1 / Dose 2 / Booster" labeling rules — by disease group or by exact vaccine_name match?