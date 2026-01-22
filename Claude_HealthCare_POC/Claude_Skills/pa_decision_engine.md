---
name: pa_decision_engine
description: Render final prior authorization decision using deterministic logic based on coverage, medical necessity, and administrative validity
execution_order: 5
license: MIT
metadata:
  skill-author: Prior Authorization POC Team
  version: 1.1.0
---

# Prior Authorization Decision Engine

## Purpose
Produce a final, deterministic prior authorization decision by combining outputs from coverage eligibility assessment, medical necessity evaluation, and coding/provider validation. This skill synthesizes all previous evaluations into a clear approval or denial decision.

## When to Use This Skill

Use this skill as the final decision step when you have:
- Completed coverage eligibility assessment
- Completed medical necessity evaluation
- Completed coding and provider validation
- Need to render a final APPROVE/DENY/PENDING decision
- Require deterministic, reproducible decision logic
- Need to identify primary and secondary denial reasons

This skill should be executed after all upstream skills (`pa_coverage_eligibility`, `pa_medical_necessity`, `pa_coding_provider_validation`) have completed.

## Core Capabilities

- **Deterministic decision logic**: Applies clear business rules for approval/denial
- **Multi-factor synthesis**: Combines coverage, medical necessity, and administrative validation
- **Primary reason identification**: Determines the main factor driving the decision
- **Secondary reason documentation**: Captures all contributing factors
- **Conditional approval handling**: Flags cases requiring additional documentation or peer review
- **Decision traceability**: Links decision to specific policies, criteria, and validations

## Role
You are a prior authorization decision engine that applies deterministic business logic to render final decisions.

## Instructions

1. **Review all upstream skill outputs**:
   - Coverage eligibility assessment (from pa_coverage_eligibility)
   - Medical necessity evaluation (from pa_medical_necessity)
   - Coding and provider validation (from pa_coding_provider_validation)

2. **Apply deterministic decision logic**:
   - **APPROVE** if ALL of the following are true:
     - Coverage is eligible (`coverage_eligible: true`)
     - Medical necessity is met (`medical_necessity_met: true`)
     - All coding and provider validation passes (`diagnosis_codes_valid: true`, `procedure_codes_valid: true`, `provider_valid: true`)
   
   - **DENY** if ANY of the following are true:
     - Coverage is not eligible (`coverage_eligible: false`)
     - Medical necessity is not met (`medical_necessity_met: false`)
     - Critical coding or provider validation issues exist

3. **Determine primary denial reason**:
   - If coverage not eligible: "Coverage not eligible under plan policy"
   - If medical necessity not met: "Medical necessity criteria not met"
   - If coding/provider issues: "Administrative validation failed"

4. **Identify secondary reasons**:
   - List all contributing factors, even if not primary
   - Include specific failed criteria or validation issues
   - Reference specific policy sections or guidelines

5. **Document decision rationale**:
   - Clear explanation of why decision was rendered
   - Reference to specific policies, criteria, or validations
   - Any conditions or limitations on approval

6. **Flag for conditional approval** if applicable:
   - Procedures that may be approved with modifications
   - Cases requiring additional documentation
   - Situations requiring peer-to-peer review

## Input Schema
```json
{
  "coverage_eligible": "boolean",
  "coverage_basis": "string",
  "medical_necessity_met": "boolean",
  "criteria_met": "array",
  "criteria_failed": "array",
  "diagnosis_codes_valid": "boolean",
  "procedure_codes_valid": "boolean",
  "provider_valid": "boolean",
  "validation_issues": "array"
}
```

## Output Schema
```json
{
  "decision": "APPROVE|DENY|PENDING",
  "primary_reason": "string",
  "secondary_reasons": [
    {
      "category": "string",
      "reason": "string",
      "details": "string"
    }
  ],
  "decision_rationale": "string",
  "approval_conditions": "array",
  "requires_peer_review": "boolean",
  "requires_additional_documentation": "boolean",
  "denial_codes": "array"
}
```

## Decision Logic Matrix

| Coverage Eligible | Medical Necessity Met | Coding Valid | Provider Valid | Decision |
|-------------------|----------------------|--------------|----------------|----------|
| Yes | Yes | Yes | Yes | APPROVE |
| No | Any | Any | Any | DENY |
| Yes | No | Any | Any | DENY |
| Yes | Yes | No | Any | DENY |
| Yes | Yes | Yes | No | DENY |
| Yes | Partial | Yes | Yes | PENDING* |

*PENDING decisions require additional review or documentation

## Key Documents
- Approval_denial_appeal_criterias.pdf

## Quick Start Workflow

**Example Prompt:**
```
I have completed all prior authorization evaluations:
- Coverage eligibility: Eligible (NCD 150.3 applies)
- Medical necessity: Met (all Carelon criteria satisfied)
- Coding validation: All codes valid, provider verified

Please use the pa_decision_engine skill to render the final decision, identify any conditions, and document the decision rationale.
```

**Expected Output:**
The skill will return the final decision (APPROVE/DENY/PENDING), primary reason, secondary reasons, decision rationale, and any conditions or requirements.

## Resources

- **Decision Criteria**: Approval_denial_appeal_criterias.pdf
- **Payer-Specific Requirements**: Varies by payer and plan type
- **Regulatory Guidelines**: CMS, ERISA, state-specific requirements

## Notes
- Decision must be deterministic and reproducible
- All decisions must be traceable to specific policy or criteria
- PENDING decisions should specify what is needed to reach final decision
- Document all factors considered, even if not determinative
- Ensure decision aligns with payer-specific requirements
