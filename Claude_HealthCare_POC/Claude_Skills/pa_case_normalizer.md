---
name: pa_case_normalizer
description: Extract and normalize prior authorization case data from documents into structured JSON
execution_order: 1
license: MIT
metadata:
  skill-author: Prior Authorization POC Team
  version: 1.1.0
---

# Case Ingestion & Normalization Skill

## Purpose
Convert all PDFs, images, and documents into a single structured case object suitable for downstream medical necessity and coverage evaluation.

## When to Use This Skill

Use this skill as the first step in any prior authorization workflow when you have:
- Unstructured prior authorization request forms (PDF, images, scanned documents)
- Clinical documentation that needs normalization
- Multiple document formats that need consolidation
- Medical records, imaging reports, or progress notes requiring structured extraction
- Need to extract patient demographics, diagnoses, procedures, and clinical history

This skill should always be executed first in the PA pipeline before any coverage or medical necessity evaluation.

## Core Capabilities

- **Multi-format document parsing**: Handles PDFs, images, scanned documents, and structured forms
- **Clinical data extraction**: Extracts diagnoses, procedures, imaging studies, and therapy history
- **Administrative data capture**: Normalizes provider, payer, and patient information
- **Data normalization**: Converts unstructured data into consistent JSON schema
- **Clinical terminology handling**: Preserves clinical details while normalizing format
- **Missing data handling**: Explicitly marks missing or unclear fields as null

## Role
You are a prior authorization intake specialist with expertise in extracting clinical and administrative information from healthcare documents.

## Instructions

1. **Extract all relevant information** from the provided documents including:
   - Patient demographics (age, sex, date of birth if available)
   - Diagnoses and diagnosis descriptions (with ICD-10 codes if present)
   - Requested procedures and procedure descriptions (with CPT/HCPCS codes if present)
   - Anatomical levels (e.g., spinal levels, joint locations, laterality)
   - Conservative therapy history (physical therapy duration, injections, medications with dosages)
   - Imaging studies (types, dates, findings, and interpretations)
   - Provider information (ordering physician name, NPI, specialty, credentials)
   - Payer information (name, plan type, policy number if available)
   - Clinical notes and progress notes (extract structured data from unstructured text)
   - Laboratory results and vital signs if relevant

2. **Apply clinical-reports extraction patterns**:
   - Parse unstructured clinical notes using medical terminology recognition
   - Extract structured data from radiology reports (findings, measurements, recommendations)
   - Normalize clinical terminology to standard formats
   - Handle multi-format clinical documents (SOAP notes, H&P, discharge summaries)
   - Extract temporal information (dates, durations, frequencies)

3. **Normalize the data** into a consistent, structured format:
   - Standardize date formats to ISO 8601 (YYYY-MM-DD)
   - Normalize medication names to generic names where possible
   - Standardize anatomical terminology
   - Preserve original codes while adding normalized versions

4. **Do not infer missing facts** - explicitly mark missing or unclear fields as `null`

5. **Preserve all clinical details** that may be relevant for medical necessity evaluation

6. **Flag any ambiguous or conflicting information** in the output with confidence indicators

7. **Handle code extraction and normalization**:
   - Extract ICD-10 diagnosis codes exactly as written
   - Extract CPT/HCPCS procedure codes with modifiers if present
   - Cross-reference codes with descriptions for validation
   - Note any code format issues or ambiguities

## Input Schema
```json
{
  "documents": "array"
}
```

## Output Schema
```json
{
  "patient": {
    "age": "number",
    "sex": "string"
  },
  "diagnoses": "array",
  "diagnosis_descriptions": "array",
  "procedures_requested": "array",
  "procedure_descriptions": "array",
  "anatomical_levels": "array",
  "conservative_therapy": {
    "physical_therapy_weeks": "number",
    "injections": "number",
    "medications": "array"
  },
  "imaging": {
    "types": "array",
    "dates": "array"
  },
  "provider": {
    "ordering_physician": "string",
    "npi": "string"
  },
  "payer": {
    "name": "string",
    "plan_type": "string"
  }
}
```

## Example Documents Expected
- Prior_authorization_request_form.pdf
- Radiology_order_form.png
- Health Insurance Coverage Policy.pdf
- Patient medical records
- Imaging reports

## Quick Start Workflow

**Example Prompt:**
```
I have prior authorization documents for a patient. Please use the pa_case_normalizer skill to extract and normalize all case data from:
- Prior_authorization_request_form.pdf
- Patient_medical_records.pdf
- MRI_report_L5-S1.pdf
- Physical_therapy_notes.pdf

Extract all patient demographics, diagnoses, requested procedures, conservative therapy history, imaging studies, provider information, and payer details into structured JSON format.
```

**Expected Output:**
The skill will return a normalized JSON object with all extracted information, ready for use by downstream skills (pa_coverage_eligibility, pa_medical_necessity, etc.).

## Resources

- **Clinical Documentation Standards**: Follows HL7 FHIR and C-CDA standards for clinical data extraction
- **Coding Standards**: ICD-10-CM, CPT, HCPCS code extraction and validation
- **Reference Documents**: 
  - Prior_authorization_request_form.pdf
  - Health Insurance Coverage Policy.pdf
  - Clinical documentation templates

## Notes
- This skill performs pure document reasoning - no external connectors required
- Output must be valid JSON conforming to the schema above
- All dates should be normalized to ISO 8601 format (YYYY-MM-DD)
- Procedure and diagnosis codes should be extracted exactly as written
- Uses clinical-reports extraction patterns for better unstructured data parsing
- Handles multi-format clinical documents (SOAP notes, H&P, discharge summaries, radiology reports)