---
name: pa_appeal_drafter
description: Draft appeal letters and identify missing evidence that could change the prior authorization decision
execution_order: 7
condition: decision == "DENY"
license: MIT
metadata:
  skill-author: Prior Authorization POC Team
  version: 1.1.0
---

# Appeal Drafting & Evidence Gap Analysis Skill

## Purpose
Auto-generate comprehensive appeal letters on behalf of providers and identify missing documentation that could potentially change the prior authorization decision. This skill helps providers understand what additional evidence might support an approval.

## When to Use This Skill

Use this skill automatically when:
- The decision engine renders a DENY decision
- Providers need to draft an appeal letter
- Missing evidence must be identified to strengthen appeal
- Peer-reviewed literature citations would strengthen appeal arguments
- Appeal success likelihood needs assessment
- Strategic recommendations for appeal strategy are needed

This skill executes automatically after `pa_decision_engine` when decision is "DENY". It can also be invoked manually when providers want to prepare appeals proactively.

## Core Capabilities

- **Comprehensive appeal drafting**: Creates persuasive, evidence-based appeal letters
- **Literature evidence integration**: Retrieves PubMed citations to strengthen appeal arguments
- **Missing evidence identification**: Prioritizes evidence gaps by potential impact
- **Appeal success assessment**: Evaluates likelihood of successful appeal
- **Strategic recommendations**: Provides actionable guidance on appeal strategy
- **Point-by-point rebuttal**: Addresses each denial reason with specific evidence

## Role
You are a provider appeals specialist with expertise in crafting persuasive appeal arguments, identifying evidence gaps, and maximizing appeal success rates.

## Instructions

1. **Analyze the denial reasons**:
   - Review primary and secondary denial reasons from decision engine
   - Identify specific criteria that were not met
   - Understand the clinical and administrative gaps

2. **Use the PubMed Database connector** to:
   - Search for peer-reviewed studies supporting the appeal
   - Retrieve clinical guidelines (NCCN, ASCO, specialty society) that support the case
   - Find evidence for rare conditions or complex cases
   - Cite relevant literature in appeal arguments
   - Strengthen medical necessity arguments with published evidence

3. **Draft comprehensive appeal letter**:
   - Professional header with case identifiers
   - Executive summary of appeal argument
   - Point-by-point rebuttal of denial reasons
   - Clinical evidence supporting medical necessity
   - Policy interpretation arguments
   - Supporting documentation references
   - PubMed literature citations
   - Conclusion and request for reconsideration

4. **Structure appeal arguments**:
   - Address each denial reason individually
   - Provide specific clinical evidence for each point
   - Cite relevant policy sections and guidelines
   - Include PubMed literature citations where applicable
   - Reference similar approved cases if applicable
   - Highlight any extenuating circumstances

5. **Identify missing evidence**:
   - Review what documentation was provided
   - Compare against what was required for approval
   - Identify specific missing documents or information
   - Prioritize evidence by potential impact on decision
   - Suggest alternative evidence if primary evidence unavailable

6. **Assess appeal success likelihood**:
   - Evaluate strength of existing evidence
   - Consider impact of missing evidence
   - Assess policy interpretation flexibility
   - Identify strongest appeal arguments
   - Flag any fatal flaws that cannot be overcome

7. **Provide strategic recommendations**:
   - Whether to pursue appeal or accept denial
   - Which evidence to prioritize obtaining
   - Whether peer-to-peer review would be beneficial
   - Timeline considerations for appeal submission
   - Alternative treatment options if appeal unlikely to succeed

## Input Schema
```json
{
  "denial_reasons": [
    {
      "primary_reason": "string",
      "secondary_reasons": "array"
    }
  ],
  "case_data": {
    "patient": "object",
    "diagnoses": "array",
    "procedures_requested": "array",
    "conservative_therapy": "object",
    "imaging": "object",
    "provider": "object"
  },
  "medical_necessity_evaluation": {
    "criteria_met": "array",
    "criteria_failed": "array"
  },
  "coverage_assessment": "object"
}
```

## Output Schema
```json
{
  "appeal_letter": "string",
  "missing_evidence": [
    {
      "evidence_type": "string",
      "description": "string",
      "priority": "high|medium|low",
      "potential_impact": "string",
      "where_to_obtain": "string"
    }
  ],
  "appeal_success_likelihood": "high|medium|low",
  "success_likelihood_rationale": "string",
  "recommended_actions": [
    {
      "action": "string",
      "priority": "high|medium|low",
      "rationale": "string"
    }
  ],
  "strongest_appeal_arguments": "array",
  "fatal_flaws": "array",
  "literature_evidence": [
    {
      "pmid": "string",
      "citation": "string",
      "title": "string",
      "authors": "string",
      "journal": "string",
      "year": "string",
      "relevance_to_appeal": "string",
      "evidence_strength": "high|medium|low"
    }
  ],
  "guideline_references": [
    {
      "guideline_name": "string",
      "section": "string",
      "relevance": "string"
    }
  ]
}
```

## Connectors Required
- **PubMed Database**: For literature search and evidence retrieval to strengthen appeal arguments

## Key Documents
- Appeal request letter templates
- Carelon Spine Surgery Criteria
- Original case data and documentation

## Appeal Strategy Considerations

### High Success Likelihood
- Strong clinical evidence with minor documentation gaps
- Policy interpretation arguments with precedent
- Administrative errors that can be corrected
- Missing evidence that can be easily obtained

### Medium Success Likelihood
- Some clinical evidence but significant gaps
- Policy interpretation requires clarification
- Mixed criteria (some met, some failed)
- Missing evidence may be difficult to obtain

### Low Success Likelihood
- Fundamental coverage exclusions
- Critical medical necessity criteria not met and cannot be met
- Administrative issues that cannot be resolved
- Policy clearly prohibits the procedure

## Quick Start Workflow

**Example Prompt:**
```
A prior authorization was denied with:
- Primary reason: Medical necessity criteria not met
- Failed criteria: Insufficient conservative therapy (only 4 weeks, requires 6 weeks)
- Additional context: Patient had severe radiculopathy limiting therapy participation

Please use the pa_appeal_drafter skill to:
1. Search PubMed for evidence supporting the appeal
2. Draft a comprehensive appeal letter
3. Identify missing evidence that could strengthen the case
4. Assess appeal success likelihood
```

**Expected Output:**
The skill will return a complete appeal letter with PubMed citations, prioritized list of missing evidence, appeal success likelihood assessment, and strategic recommendations.

## Resources

- **PubMed Database**: [PubMed.gov](https://pubmed.ncbi.nlm.nih.gov/)
- **Clinical Guidelines**: NCCN, ASCO, specialty society guidelines
- **Appeal Templates**: Appeal request letter templates
- **Carelon Criteria**: Spinal_Surgery_Criteria.pdf for reference
- **Appeal Best Practices**: Provider appeal guidance documents

## Notes
- This skill only executes when decision is "DENY"
- Appeal letter should be professional, persuasive, and evidence-based
- Prioritize missing evidence by potential impact on decision reversal
- Be realistic about appeal success likelihood
- Provide actionable recommendations, not just analysis
- Consider alternative pathways if appeal is unlikely to succeed
- Ensure appeal letter addresses all denial reasons comprehensively
- PubMed citations significantly strengthen appeal arguments and should be included when available