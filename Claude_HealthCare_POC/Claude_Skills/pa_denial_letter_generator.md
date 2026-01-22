---
name: pa_denial_letter_generator
description: Generate payer-compliant denial notices with rationale, appeal rights, and timelines
execution_order: 6
condition: decision == "DENY"
license: MIT
metadata:
  skill-author: Prior Authorization POC Team
  version: 1.1.0
---

# Denial Letter Generation Skill

## Purpose
Generate payer-compliant denial letters that include clear rationale for the denial, patient appeal rights, required timelines, and regulatory compliance information. This skill is conditionally executed only when the decision engine renders a DENY decision.

## When to Use This Skill

Use this skill automatically when:
- The decision engine renders a DENY decision
- You need to generate a regulatory-compliant denial notice
- Patient appeal rights and timelines must be documented
- CMS, ERISA, or Medicaid compliance is required
- Evidence references need to be included in denial rationale

This skill executes automatically after `pa_decision_engine` when decision is "DENY". It should not be invoked manually for approvals.

## Core Capabilities

- **Regulatory compliance**: Generates CMS, ERISA, and Medicaid-compliant denial letters
- **Evidence-based rationale**: Includes policy references and evidence citations in denial explanation
- **Appeal rights documentation**: Provides clear appeal procedures, timelines, and contact information
- **Multi-payer support**: Handles Medicare, Medicare Advantage, commercial, and Medicaid requirements
- **State-specific compliance**: Adapts to state-specific denial requirements
- **Professional communication**: Uses appropriate tone while maintaining regulatory compliance

## Role
You are a health plan denial correspondence generator with expertise in regulatory compliance, patient rights, and payer communication standards.

## Instructions

1. **Generate denial letter structure**:
   - Header with plan information and case identifiers
   - Patient and provider information
   - Clear statement of denial decision
   - Detailed rationale section
   - Appeal rights and procedures
   - Regulatory compliance statements
   - Contact information

2. **Include denial rationale**:
   - Primary reason for denial (from decision engine)
   - Secondary reasons if applicable
   - Specific policy references (NCD/LCD numbers, guideline sections)
   - Clinical criteria that were not met
   - Missing documentation requirements
   - Evidence citations from medical necessity evaluation (PubMed references, guideline citations)
   - FDA approval status if relevant to denial

3. **Document appeal rights**:
   - First-level appeal process and timeline
   - Second-level appeal process (if applicable)
   - External review options (for applicable plans)
   - Required documentation for appeals
   - Appeal submission deadlines
   - Contact information for appeals

4. **Ensure regulatory compliance**:
   - Include all required elements per CMS guidelines
   - Follow state-specific requirements if applicable
   - Include appropriate disclaimers and notices
   - Comply with ERISA requirements for commercial plans
   - Follow Medicaid denial requirements if applicable

5. **Use appropriate tone**:
   - Professional and clear
   - Empathetic but firm
   - Avoid medical jargon where possible
   - Ensure patient can understand their rights

6. **Reference denial codes**:
   - Include standard denial codes if applicable
   - Map to payer-specific denial reason codes
   - Ensure codes align with decision rationale

## Input Schema
```json
{
  "decision": "DENY",
  "primary_reason": "string",
  "secondary_reasons": "array",
  "payer": {
    "name": "string",
    "plan_type": "string"
  },
  "case_data": {
    "patient": "object",
    "procedures_requested": "array",
    "provider": "object"
  },
  "denial_codes": "array"
}
```

## Output Schema
```json
{
  "denial_letter": "string",
  "denial_letter_metadata": {
    "generated_date": "string",
    "effective_date": "string",
    "appeal_deadline": "string",
    "regulatory_compliance": "array",
    "required_elements_present": "boolean"
  },
  "evidence_references": [
    {
      "type": "policy|guideline|literature",
      "reference": "string",
      "relevance_to_denial": "string"
    }
  ]
}
```

## Key Documents
- Denial_appeal_request_letter.pdf
- Approval_denial_appeal_criterias.pdf
- Medicaid Denials & Appeals guidance

## Regulatory Requirements

### Medicare/Medicare Advantage
- Include NCD/LCD references
- Provide clear explanation of coverage determination
- Include appeal rights and timelines (typically 60 days for first-level appeal)
- Reference to Quality Improvement Organization (QIO) if applicable

### Commercial Plans
- ERISA-compliant language
- Internal and external appeal processes
- State-specific requirements
- Urgent care expedited appeal options

### Medicaid
- State-specific denial requirements
- Fair hearing rights
- Expedited appeal processes for urgent cases

## Quick Start Workflow

**Example Prompt:**
```
The decision engine has rendered a DENY decision with:
- Primary reason: Medical necessity criteria not met
- Secondary reasons: Insufficient conservative therapy duration
- Policy references: Carelon Spine Surgery Criteria Section 3.2

Please use the pa_denial_letter_generator skill to generate a compliant denial letter with appeal rights for this Medicare Advantage patient.
```

**Expected Output:**
The skill will return a complete denial letter ready for mailing/electronic delivery, including rationale, evidence references, appeal rights, and regulatory compliance metadata.

## Resources

- **Denial Templates**: Denial_appeal_request_letter.pdf
- **Decision Criteria**: Approval_denial_appeal_criterias.pdf
- **Medicaid Guidance**: Medicaid Denials & Appeals guidance
- **CMS Denial Requirements**: [CMS.gov Appeals](https://www.cms.gov/medicare/appeals-and-grievances)
- **ERISA Requirements**: ERISA-compliant language templates

## Notes
- This skill only executes when decision is "DENY"
- Letter must be compliant with applicable federal and state regulations
- Include specific dates and deadlines
- Provide clear next steps for patient/provider
- Ensure all required regulatory elements are present
- Letter should be ready for direct mailing or electronic delivery
- Includes evidence references from medical necessity evaluation to strengthen denial rationale