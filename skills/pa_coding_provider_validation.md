---
name: pa_coding_provider_validation
description: Validate diagnosis codes, procedure codes, and provider identifiers to eliminate administrative denials
execution_order: 4
license: MIT
metadata:
  skill-author: Prior Authorization POC Team
  version: 1.1.0
---

# Coding & Provider Validation Skill

## Purpose
Validate that all diagnosis codes (ICD-10), procedure codes (CPT/HCPCS), and provider identifiers (NPI) are valid, active, and correctly formatted. This prevents administrative denials due to coding errors.

## When to Use This Skill

Use this skill after case normalization when you need to:
- Validate ICD-10 diagnosis codes before medical necessity evaluation
- Verify CPT/HCPCS procedure codes are valid and billable
- Check provider NPI and credentials are active
- Identify coding errors that would cause administrative denials
- Cross-reference codes between ICD-9/ICD-10 if historical data present
- Validate code hierarchies and temporal validity
- Check for code bundling or modifier requirements

This skill should be executed after `pa_case_normalizer` and can run in parallel with `pa_coverage_eligibility` and `pa_medical_necessity`.

## Core Capabilities

- **ICD-10 validation**: Verifies diagnosis codes are valid, active, and appropriate for date of service
- **CPT/HCPCS validation**: Checks procedure codes are billable and correctly formatted
- **Provider credentialing**: Validates NPI, specialty, and license status
- **Code hierarchy validation**: Checks parent-child code relationships
- **Temporal code validation**: Verifies codes are valid for specific dates (handles code changes over time)
- **Code mapping**: Cross-references ICD-9 to ICD-10, CPT to HCPCS
- **Modifier validation**: Checks required or appropriate modifiers for procedures

## Role
You are a claims validation specialist with expertise in medical coding standards and provider credentialing.

## Instructions

1. **Validate Diagnosis Codes (ICD-10)**:
   - Use the ICD-10 connector to verify each diagnosis code is valid
   - Check that codes are active (not deleted or replaced)
   - Verify code format and structure
   - Confirm codes are appropriate for the date of service
   - Check for any code-specific requirements or restrictions
   - Cross-reference ICD-9 codes to ICD-10 if historical data present
   - Validate code hierarchy (parent-child relationships)
   - Check temporal validity (code changes over time)

2. **Validate Procedure Codes (CPT/HCPCS)**:
   - Verify each procedure code is valid and billable
   - Check code status (active, deleted, replaced)
   - Verify code format and structure
   - Confirm codes are appropriate for the date of service
   - Check for any bundling or modifier requirements
   - Map CPT codes to HCPCS equivalents if applicable
   - Validate code hierarchies and relationships
   - Check temporal validity for code changes

3. **Validate Provider Information**:
   - Use the NPI Registry connector to verify the provider NPI
   - Confirm the NPI is active and not revoked
   - Verify the provider's specialty matches the procedure type
   - Check provider credentials and license status
   - Validate provider name matches NPI record

4. **Check for Common Administrative Issues**:
   - Missing or invalid modifiers
   - Inappropriate code combinations
   - Outdated codes (replaced by newer versions)
   - Formatting errors (extra spaces, incorrect characters)

5. **Document all issues** found, including:
   - Specific code or identifier with issue
   - Type of issue (invalid, inactive, format error, etc.)
   - Recommended correction
   - Severity (critical, warning, informational)

## Input Schema
```json
{
  "diagnoses": "array",
  "procedures_requested": "array",
  "provider": {
    "ordering_physician": "string",
    "npi": "string"
  }
}
```

## Output Schema
```json
{
  "diagnosis_codes_valid": "boolean",
  "procedure_codes_valid": "boolean",
  "provider_valid": "boolean",
  "issues": [
    {
      "type": "string",
      "category": "diagnosis|procedure|provider",
      "code_or_identifier": "string",
      "issue": "string",
      "severity": "critical|warning|informational",
      "recommendation": "string"
    }
  ],
  "validation_summary": {
    "total_diagnosis_codes": "number",
    "valid_diagnosis_codes": "number",
    "total_procedure_codes": "number",
    "valid_procedure_codes": "number",
    "provider_status": "string"
  }
}
```

## Connectors Required
- **ICD-10 Database**: For diagnosis code validation
- **NPI Registry**: For provider NPI validation

## Where to get tool inputs
Get diagnosis codes from Input **diagnoses** and call `lookup_icd10(code=...)` or `lookup_icd10(condition=...)` per diagnosis. Get procedure codes from Input **procedures_requested** and call `lookup_cpt(code=...)` per code. Get NPI from Input **provider.npi** and call `lookup_npi(npi=...)`. Extract these values from the Input; do not call tools without them.

## Quick Start Workflow

**Example Prompt:**
```
I have a normalized case with:
- Diagnosis codes: M54.5, M51.26
- Procedure codes: CPT 22633, CPT 22842
- Provider NPI: 1234567890

Please use the pa_coding_provider_validation skill to:
1. Validate all ICD-10 diagnosis codes
2. Verify CPT procedure codes are valid and billable
3. Check provider NPI and credentials
4. Identify any coding issues that need correction
```

**Expected Output:**
The skill will return validation status for each code category, detailed list of any issues found with severity levels, and specific recommendations for corrections.

## Resources

- **ICD-10-CM Official Guidelines**: [CMS ICD-10](https://www.cms.gov/medicare/icd-10)
- **CPT Code Lookup**: [AMA CPT Code Database](https://www.ama-assn.org/practice-management/cpt)
- **HCPCS Codes**: [CMS HCPCS](https://www.cms.gov/medicare/coding/medhcpcsgeninfo)
- **NPI Registry**: [NPPES NPI Registry](https://npiregistry.cms.hhs.gov/)
- **Code Mapping Tools**: ICD-9 to ICD-10 crosswalks, CPT to HCPCS mappings

## Notes
- A single invalid code or identifier can cause administrative denial
- Critical issues must be resolved before proceeding to decision
- Warnings may not prevent approval but should be documented
- Always provide specific recommendations for fixing issues
- Check for code updates or replacements that may affect validity
- Uses PyHealth-style coding standardization patterns for better code handling
- Validates temporal code validity (codes change over time, must check date-specific validity)