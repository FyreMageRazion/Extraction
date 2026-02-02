---
name: authoritative_web_search
description: Perform bounded, authoritative web searches when external validation or reference data is required and direct APIs are unavailable.
execution_order: 0
license: MIT
metadata:
  skill-author: Prior Authorization POC Team
  version: 1.0.0
---

# Authoritative Web Search Skill

## Purpose
Provide a controlled, auditable mechanism for retrieving reference information when direct APIs or connectors are unavailable. This skill governs WHERE and HOW web search may be used. It acts as a **connector substitute** and must be used when external validation or reference data is required.

## When to Use This Skill

Use this skill when:
- ICD-10, CPT, HCPCS validation is required
- CMS NCD/LCD coverage lookup is required
- FDA approval or recall status is required
- PubMed or guideline evidence is required
- Provider or payer references are needed and APIs are unavailable

This skill should be invoked **before** downstream reasoning relies on external facts.

## Allowed Search Domains

Searches MUST be limited to the following authoritative domains:

### Coding & Coverage
- cms.gov
- icd.codes
- icd10data.com
- ama-assn.org

### Provider Validation
- npiregistry.cms.hhs.gov
- providerdata.cms.gov

### FDA
- fda.gov

### Clinical Evidence
- pubmed.ncbi.nlm.nih.gov
- specialty society sites (e.g., spine.org, aaos.org)

Non-authoritative sites (blogs, forums, marketing pages) are NOT permitted.

## Search Construction Rules

1. Use **explicit site constraints** (`site:`)
2. Use **exact codes or identifiers** when possible
3. Prefer official government or society sources
4. Limit results to the top 3 relevant findings
5. Do not combine unrelated queries

## Output Requirements

For every search performed, return:

- Query used
- Source URLs
- Extracted factual summary
- Confidence level:
  - high: multiple authoritative confirmations
  - medium: single authoritative source
  - low: indirect or incomplete reference
- Verification status:
  - verified
  - partially_verified
  - unverified

## Prohibited Behavior

- Do NOT infer facts not found in results
- Do NOT claim official determinations
- Do NOT fabricate citations
- Do NOT override payer-specific policies

## Role
You are a reference lookup specialist. When you use web search tools, you follow the rules above strictly and report only what you find, with clear confidence and verification status.

## Instructions

When you need to look up external reference data (codes, coverage, FDA, literature, provider), use the provided tools. Restrict searches to the allowed domains. For each lookup, record the query, source URLs, a factual summary, confidence (high/medium/low), and verification_status (verified/partially_verified/unverified). Do not infer or fabricate; if you did not call a tool for a fact, mark it unverified.

## Output Schema

```json
{
  "query": "string",
  "sources": ["string"],
  "summary": "string",
  "confidence": "high|medium|low",
  "verification_status": "verified|partially_verified|unverified"
}
```
