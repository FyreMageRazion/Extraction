---
name: Prior Authorization POC Agent
overview: Build an interactive CLI agent using Claude SDK that orchestrates the 7 existing prior authorization skills to process PA requests and generate appeals. The agent will use stub connectors for testing and provide a chat-based interface similar to the research agent example.
todos:
  - id: setup_project_structure
    content: Create project directory structure (prior_auth_agent/, utils/, connectors/, prompts/)
    status: pending
  - id: create_requirements
    content: Create requirements.txt with claude-agent-sdk and python-dotenv
    status: pending
  - id: create_env_example
    content: Create .env.example with ANTHROPIC_API_KEY template
    status: pending
  - id: implement_session_utils
    content: Implement session.py for session directory management
    status: pending
  - id: implement_transcript_utils
    content: Implement transcript.py for conversation logging
    status: pending
  - id: create_lead_agent_prompt
    content: Create lead_agent.txt prompt that orchestrates the 7 skills
    status: pending
  - id: implement_stub_connectors
    content: Implement all 5 stub connectors (CMS, FDA, PubMed, ICD-10, NPI) with mock responses
    status: pending
  - id: implement_main_agent
    content: Implement agent.py with ClaudeSDKClient, skill loading, and interactive CLI
    status: pending
  - id: update_readme
    content: Update README.md with agent usage instructions and setup guide
    status: pending
---

# Prior Authorization and Appeals POC Agent

## Overview

Build an interactive CLI agent using the Claude SDK that orchestrates the 7 existing prior authorization skills to process PA requests from documents in the `Inputs/` directory. The agent will follow the research agent pattern with session management, transcript logging, and skill orchestration.

https://platform.claude.com/docs/en/build-with-claude/skills-guide

https://github.com/anthropics/claude-agent-sdk-demos/blob/main/research-agent/research_agent/agent.py

https://github.com/anthropics/claude-agent-sdk-python/tree/main/examples

## Architecture

The agent will:

1. Load documents from `Inputs/` directory
2. Orchestrate skills in execution order (pa_case_normalizer → pa_coverage_eligibility → pa_medical_necessity → pa_coding_provider_validation → pa_decision_engine → conditional denial/appeal skills)
3. Use stub connectors for testing (CMS, FDA, PubMed, ICD-10, NPI)
4. Provide interactive CLI for processing requests
5. Generate structured outputs and save session transcripts

## Project Structure

```
e:\Claude_HealthCare_PriorAuth\
├── .claude/
│   └── skills/          # Existing 7 skills (already present)
├── Inputs/               # Input PDFs (already present)
├── prior_auth_agent/
│   ├── __init__.py
│   ├── agent.py          # Main agent entry point
│   ├── prompts/
│   │   └── lead_agent.txt  # System prompt for orchestrating skills
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── session.py    # Session directory setup
│   │   ├── transcript.py # Transcript writing
│   │   └── connectors.py # Stub connector implementations
│   └── connectors/
│       ├── __init__.py
│       ├── cms_stub.py    # CMS Coverage Database stub
│       ├── fda_stub.py    # FDA Database stub
│       ├── pubmed_stub.py # PubMed Database stub
│       ├── icd10_stub.py  # ICD-10 Database stub
│       └── npi_stub.py    # NPI Registry stub
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variable template
└── README.md             # Updated with agent usage
```

## Implementation Details

### 1. Main Agent (`prior_auth_agent/agent.py`)

- Use `ClaudeSDKClient` with `ClaudeAgentOptions`
- Load skills from `.claude/skills/` using `setting_sources=["project"]`
- Create lead agent prompt that orchestrates the 7 skills in sequence
- Handle conditional skill execution (denial letter and appeal only on DENY)
- Stream responses and process tool calls
- Save session transcripts and outputs

Key features:

- Interactive chat loop
- Document loading from `Inputs/` directory
- Skill orchestration following execution_order
- Session management with unique directories
- Transcript logging

### 2. Lead Agent Prompt (`prior_auth_agent/prompts/lead_agent.txt`)

Create a system prompt that:

- Explains the prior authorization workflow
- Lists all 7 skills and their execution order
- Instructs when to use each skill
- Handles conditional execution (denial/appeal only on DENY)
- Guides document processing from Inputs directory
- Explains how to chain skill outputs

### 3. Session Management (`prior_auth_agent/utils/session.py`)

- Create unique session directories with timestamps
- Structure: `sessions/YYYY-MM-DD_HH-MM-SS/`
- Store transcripts, outputs, and intermediate results
- Return session path and transcript file path

### 4. Transcript Writer (`prior_auth_agent/utils/transcript.py`)

- Write conversation transcripts to file
- Support both console and file output
- Format tool calls and responses
- Track skill execution flow

### 5. Stub Connectors (`prior_auth_agent/connectors/`)

Create mock implementations for testing:

**CMS Coverage Database Stub** (`cms_stub.py`):

- Mock NCD/LCD lookup responses
- Return sample policy references
- Simulate coverage determination logic

**FDA Database Stub** (`fda_stub.py`):

- Mock device/drug approval status
- Return sample FDA approval data
- Simulate indication matching

**PubMed Database Stub** (`pubmed_stub.py`):

- Mock PubMed search results
- Return sample literature citations
- Simulate evidence retrieval

**ICD-10 Database Stub** (`icd10_stub.py`):

- Mock ICD-10 code validation
- Return code validity and descriptions
- Simulate code lookup

**NPI Registry Stub** (`npi_stub.py`):

- Mock NPI validation
- Return provider information
- Simulate credential verification

All stubs should:

- Accept the same parameters as real connectors would
- Return realistic sample data
- Log calls for debugging
- Be easily replaceable with real MCP connectors later

### 6. Dependencies (`requirements.txt`)

- `claude-agent-sdk` - Claude SDK for agents
- `python-dotenv` - Environment variable management
- `pathlib` - Path handling (built-in, but document usage)

### 7. Environment Setup (`.env.example`)

- `ANTHROPIC_API_KEY` - Required for Claude API access

## Workflow Flow

```
User Input → Lead Agent → Skill Orchestration:
  1. pa_case_normalizer (extract from documents)
  2. pa_coverage_eligibility (check coverage)
  3. pa_medical_necessity (evaluate criteria)
  4. pa_coding_provider_validation (validate codes)
  5. pa_decision_engine (render decision)
  6. pa_denial_letter_generator (if DENY)
  7. pa_appeal_drafter (if DENY)
→ Final Output → Session Transcript
```

## Key Implementation Notes

1. **Skill Loading**: Use `setting_sources=["project"] `to load skills from `.claude/skills/`
2. **Tool Configuration**: Enable `Skill` tool in `allowed_tools` to use skills
3. **Conditional Execution**: Lead agent prompt should instruct conditional skill execution based on decision
4. **Document Handling**: Agent should reference files in `Inputs/` directory when processing
5. **Output Management**: Save structured outputs (JSON) to session directory
6. **Error Handling**: Graceful handling of missing documents or skill execution failures

## Testing Strategy

1. Test with existing PDFs in `Inputs/` directory
2. Verify skill execution order
3. Test both approval and denial flows
4. Validate conditional skill execution (denial/appeal only on DENY)
5. Check transcript and output file generation
6. Verify stub connector responses

## Future Enhancements

- Replace stub connectors with real MCP connectors
- Add batch processing mode
- Add web interface
- Add database for case tracking
- Add API endpoints for integration