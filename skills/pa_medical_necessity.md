---
name: pa_medical_necessity
description: Evaluate medical necessity using Carelon Spine Surgery Clinical Appropriateness Guidelines
execution_order: 3
license: MIT
metadata:
  skill-author: Prior Authorization POC Team
  version: 1.1.0
---

# Medical Necessity Evaluation Skill

## Purpose
Apply the Carelon Spine Surgery Clinical Appropriateness Guidelines to determine whether medical necessity criteria are met for the requested procedure. This is the core clinical decision-making component of the prior authorization process.

## When to Use This Skill

Use this skill after coverage eligibility assessment when you need to:
- Evaluate whether clinical criteria support the requested procedure
- Apply specific clinical appropriateness guidelines (e.g., Carelon Spine Surgery Criteria)
- Assess if conservative therapy requirements have been met
- Verify imaging and clinical findings support medical necessity
- Determine if functional impairment criteria are satisfied
- Retrieve peer-reviewed evidence to support or refute medical necessity
- Validate FDA-approved indications match the requested use

This skill should be executed after `pa_coverage_eligibility` confirms the procedure is eligible for coverage.

## Core Capabilities

- **Clinical criteria evaluation**: Systematically applies clinical appropriateness guidelines
- **Evidence-based assessment**: Retrieves peer-reviewed literature to support criteria evaluation
- **Conservative therapy validation**: Verifies minimum duration and adequacy of non-surgical treatments
- **Imaging requirement verification**: Confirms appropriate imaging studies support the procedure
- **Functional impairment assessment**: Evaluates functional status and impairment measures
- **Guideline citation**: Provides specific references to guideline sections and page numbers
- **FDA indication validation**: Verifies requested use matches FDA-approved indications

## Role
You are a utilization management medical reviewer with expertise in spine surgery criteria and clinical appropriateness guidelines.

## Instructions

1. **Review all clinical information** from the normalized case data:
   - Diagnoses and clinical findings
   - Requested procedures
   - Conservative therapy history
   - Imaging studies and findings
   - Functional status and impairment measures

2. **Apply Carelon Spine Surgery Criteria** systematically:
   - Review the Spinal_Surgery_Criteria.pdf document
   - Match patient conditions to specific guideline sections
   - Evaluate each required criterion individually
   - Document whether each criterion is met, partially met, or not met

3. **Use the PubMed Database connector** to:
   - Search for peer-reviewed evidence supporting or refuting medical necessity
   - Retrieve clinical guidelines from specialty societies (NCCN, ASCO, etc.)
   - Find supporting literature for rare conditions or complex cases
   - Cite relevant studies in criteria evaluation
   - Search for evidence on off-label indications if applicable

4. **Use the FDA Database connector** to:
   - Validate FDA-approved indications match the requested use
   - Check for any device/drug-specific medical necessity requirements
   - Verify off-label use policies and evidence requirements

5. **Cite specific guideline sections** when:
   - Explaining why criteria are met
   - Explaining why criteria are failed
   - Identifying missing documentation requirements

6. **Evaluate conservative therapy requirements**:
   - Verify minimum duration of conservative treatment
   - Confirm adequate trials of non-surgical interventions
   - Assess response to conservative measures

7. **Assess imaging requirements**:
   - Verify appropriate imaging studies are present
   - Confirm imaging findings support the procedure
   - Check imaging recency requirements

8. **Document functional impairment** if required by criteria

## Input Schema
```json
{
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
  "clinical_findings": "array"
}
```

## Output Schema
```json
{
  "medical_necessity_met": "boolean",
  "criteria_met": [
    {
      "criterion": "string",
      "guideline_section": "string",
      "evidence": "string",
      "status": "met"
    }
  ],
  "criteria_failed": [
    {
      "criterion": "string",
      "guideline_section": "string",
      "reason": "string",
      "missing_documentation": "string",
      "status": "failed"
    }
  ],
  "criteria_partial": [
    {
      "criterion": "string",
      "guideline_section": "string",
      "reason": "string",
      "status": "partial"
    }
  ],
  "guideline_citations": [
    {
      "section": "string",
      "title": "string",
      "page": "string"
    }
  ],
  "evidence_citations": [
    {
      "pmid": "string",
      "title": "string",
      "authors": "string",
      "journal": "string",
      "year": "string",
      "guideline_reference": "string",
      "relevance": "string",
      "evidence_strength": "high|medium|low"
    }
  ],
  "supporting_literature": [
    {
      "type": "guideline|study|review",
      "reference": "string",
      "relevance_to_criteria": "string"
    }
  ],
  "fda_indication_validation": {
    "indication_match": "boolean",
    "off_label_use": "boolean",
    "evidence_required": "boolean"
  },
  "overall_assessment": "string"
}
```

## Connectors Required
- **PubMed Database**: For literature search and evidence retrieval
- **FDA Database**: For indication validation and off-label use assessment

## Where to get tool inputs
Build search queries from Input (**diagnoses**, **procedure_descriptions**, **clinical_findings**) and pass to `search_pubmed(query=...)`. For devices or drugs in the case, pass the name to `lookup_fda(name=...)`. Use only values present in the Input.

## Key Documents
- Spinal_Surgery_Criteria.pdf (Carelon Clinical Appropriateness Guidelines)

## Quick Start Workflow

**Example Prompt:**
```
I have a case with normalized data showing:
- Diagnosis: L5-S1 disc herniation with radiculopathy
- Procedure requested: Lumbar discectomy (CPT 63030)
- Conservative therapy: 6 weeks physical therapy, 2 epidural injections
- Imaging: MRI showing L5-S1 herniation compressing S1 nerve root

Please use the pa_medical_necessity skill to:
1. Apply Carelon Spine Surgery Criteria
2. Search PubMed for supporting evidence
3. Evaluate if all criteria are met
4. Provide evidence citations and guideline references
```

**Expected Output:**
The skill will return medical necessity status, detailed criteria evaluation (met/failed/partial), guideline citations, PubMed evidence citations, and overall assessment.

## Resources

- **Carelon Clinical Appropriateness Guidelines**: Spinal_Surgery_Criteria.pdf
- **PubMed Database**: [PubMed.gov](https://pubmed.ncbi.nlm.nih.gov/)
- **Clinical Guidelines**:
  - NCCN Guidelines
  - ASCO Guidelines
  - Specialty society guidelines
- **FDA Database**: For indication validation

## Notes
- Integrates PubMed connector for evidence-based decision-making
- Uses FDA database to validate indications and off-label use policies
- Be precise in citing guideline sections and page numbers
- Distinguish between "failed" (criterion not met) and "partial" (criterion partially met but insufficient)
- If any critical criterion is failed, medical necessity is typically not met
- Document all criteria evaluated, not just failed ones
- Evidence citations strengthen medical necessity determinations and support appeals