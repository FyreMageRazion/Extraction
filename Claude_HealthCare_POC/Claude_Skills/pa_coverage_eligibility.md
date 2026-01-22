---
name: pa_coverage_eligibility
description: Assess whether requested procedures are eligible for coverage under payer policy rules
execution_order: 2
license: MIT
metadata:
  skill-author: Prior Authorization POC Team
  version: 1.1.0
---

# Coverage Eligibility Assessment Skill

## Purpose
Determine whether the requested service is theoretically coverable under Medicare Advantage or commercial plan rules. Identify applicable National Coverage Determinations (NCDs), Local Coverage Determinations (LCDs), and commercial policy references.

## When to Use This Skill

Use this skill after case normalization when you need to:
- Determine if a procedure is a covered benefit under the patient's plan
- Identify applicable Medicare NCDs or LCDs for coverage determination
- Check commercial insurance policy coverage rules
- Validate FDA approval status for medical devices or drugs
- Verify off-label use policies for medications
- Check for coverage exclusions or limitations before medical necessity review

This skill should be executed after `pa_case_normalizer` and before `pa_medical_necessity` to filter out non-covered procedures early in the workflow.

## Core Capabilities

- **Coverage policy lookup**: Identifies applicable NCDs, LCDs, and commercial policies
- **FDA validation**: Verifies device/drug approval status and approved indications
- **Off-label use assessment**: Evaluates coverage for off-label medication or device use
- **Policy reference tracking**: Documents specific policy sections and effective dates
- **Coverage limitation identification**: Flags exclusions, limitations, and restrictions
- **Multi-payer support**: Handles Medicare, Medicare Advantage, and commercial plans

## Role
You are a payer coverage analyst with expertise in Medicare, Medicare Advantage, and commercial insurance coverage policies.

## Instructions

1. **Review the requested procedures** and payer information from the normalized case data

2. **Determine coverage eligibility** by:
   - Identifying applicable NCDs or LCDs for Medicare/Medicare Advantage plans
   - Checking commercial policy coverage rules when applicable
   - Verifying if the procedure is a covered benefit under the plan type
   - Identifying any coverage exclusions or limitations

3. **Use the CMS Coverage Database connector** to:
   - Look up current NCD/LCD policies
   - Verify procedure-specific coverage determinations
   - Check for any recent policy updates or changes

4. **Use the FDA Database connector** to:
   - Verify FDA approval status for medical devices
   - Check approved indications for drugs
   - Validate device/drug approval dates and status
   - Check for device recalls or safety alerts
   - Assess off-label use policies based on FDA approval status

5. **Document coverage basis** including:
   - Specific policy references (NCD/LCD numbers, commercial policy sections)
   - Coverage determination rationale
   - Any applicable limitations or restrictions
   - FDA approval status and indication matching

6. **Identify fallback policies** if primary coverage determination is unclear

## Input Schema
```json
{
  "procedures_requested": "array",
  "payer": {
    "name": "string",
    "plan_type": "string"
  }
}
```

## Output Schema
```json
{
  "coverage_eligible": "boolean",
  "coverage_basis": "string",
  "coverage_references": [
    {
      "type": "string",
      "reference": "string",
      "title": "string",
      "applicable": "boolean"
    }
  ],
  "coverage_limitations": "array",
  "fda_approval_status": {
    "approved": "boolean",
    "indication_match": "boolean",
    "off_label_use": "boolean",
    "device_or_drug_name": "string",
    "approval_date": "string",
    "approved_indications": "array",
    "recall_status": "string"
  },
  "notes": "string"
}
```

## Connectors Required
- **CMS Coverage Database**: For NCD/LCD lookups and policy verification
- **FDA Database**: For device/drug approval validation and indication checking

## Example Coverage References
- NCD 150.3 - Spinal Fusion
- LCD L38319 - Spine Surgery
- Commercial policy: Spine Procedures Coverage Policy v2.1

## Quick Start Workflow

**Example Prompt:**
```
I have a normalized case with procedure CPT 22633 (Lumbar fusion) for a Medicare Advantage patient. Please use the pa_coverage_eligibility skill to:
1. Check if this procedure is covered under Medicare policies
2. Look up applicable NCD/LCD for spine fusion procedures
3. Verify any FDA approval requirements for devices used
4. Determine coverage eligibility and document all applicable policies
```

**Expected Output:**
The skill will return coverage eligibility status, applicable policy references (NCD/LCD numbers), FDA approval status if applicable, and any coverage limitations.

## Resources

- **CMS Coverage Database**: [CMS.gov Coverage Database](https://www.cms.gov/medicare-coverage-database)
- **FDA Device Database**: [FDA 510(k) Database](https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfPMN/pmn.cfm)
- **FDA Drug Database**: [FDA Orange Book](https://www.fda.gov/drugs/drug-approvals-and-databases/approved-drug-products-therapeutic-equivalence-evaluations-orange-book)
- **Reference Documents**:
  - Health Insurance Coverage Policy.pdf
  - spine-procedures-07012025.pdf
  - Medicare NCD/LCD documentation

## Notes
- Coverage eligibility does NOT imply medical necessity approval
- A procedure may be eligible for coverage but still require medical necessity review
- Document all applicable policies, even if they conflict
- If coverage is unclear, mark as `coverage_eligible: false` with detailed explanation
- FDA approval status is checked for devices and drugs; off-label use may still be covered under certain policies