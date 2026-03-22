---
name: consensus-debate
version: 1.0.0
description: |
  Multi-model consensus debate skill for complex technical decisions.
  Use when the user needs:
  - Multiple AI perspectives on a technical problem
  - Cross-review and synthesis of proposals
  - Consensus-based decision making for planning, review, architecture, or debugging
  
  Requires environment variable: LOCAL_MODEL_CONFIGS (JSON array of model configurations)
---

# Consensus Debate Skill

This skill implements a three-phase debate process to reach consensus on technical decisions:

1. **Phase 1 (Proposal)**: All models propose solutions independently (concurrent)
2. **Phase 2 (Cross-Review)**: Models review each other's proposals (concurrent)
3. **Phase 3 (Synthesis)**: Judge model synthesizes final consensus

## When to Use

Use this skill when:
- Making important architectural decisions
- Reviewing complex code changes
- Planning new features with multiple valid approaches
- Debugging difficult issues that benefit from multiple perspectives
- Any scenario where you want consensus rather than a single opinion

## Prerequisites

### Environment Variable: LOCAL_MODEL_CONFIGS

Set a JSON array with model configurations:

```json
[
  {
    "name": "model-1",
    "endpoint": "https://api.example.com/v1/chat/completions",
    "api_key": "your-api-key",
    "model": "model-id",
    "role": "participant",
    "protocol": "openai"
  },
  {
    "name": "model-2",
    "endpoint": "https://api.anthropic.com/v1",
    "api_key": "your-api-key",
    "model": "claude-3-opus",
    "role": "judge",
    "protocol": "anthropic"
  }
]
```

Required fields:
- `name`: Unique identifier for the model
- `endpoint`: API endpoint URL
- `api_key`: Authentication key
- `model`: Model identifier

Optional fields:
- `role`: "participant" or "judge" (default: "participant")
- `protocol`: "openai" or "anthropic" (default: "openai")

Requirements:
- At least 2 models configured
- Exactly 1 model with role="judge"

## Usage

```
Use the consensus-debate skill to:
- Scene: planning | review | arch | debug
- Task: [core task description]
- Content: [relevant code or context]
- Review mode: summarized | full (optional, default: summarized)
```

### Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| scene | Yes | Type of task: planning, review, arch, debug |
| task | Yes | Core task description |
| content | Yes | Relevant code, context, or documentation |
| review_mode | No | "summarized" (default) or "full" |

### Scenes

- **planning**: New feature or project planning
- **review**: Code review or quality assessment
- **arch**: Architecture or design decisions
- **debug**: Bug analysis and debugging

### Review Modes

- **summarized**: Reviewers see summarized proposals (faster, less token usage)
- **full**: Reviewers see complete proposals (more thorough, higher token cost)

## Implementation

Execute the consensus debate by:

1. Parse `LOCAL_MODEL_CONFIGS` from environment
2. Identify judge and participant models
3. Run Phase 1: Concurrent proposals from all models
4. Run Phase 2: Cross-review (each participant reviews others' proposals)
5. Run Phase 3: Judge synthesizes final consensus
6. Return structured result with:
   - `final_plan`: The synthesized consensus
   - `models_participated`: List of successful models
   - `models_failed`: List of failed models
   - `proposals`: All original proposals
   - `reviews`: All cross-reviews

## Prompt Templates

### Proposal Phase

System: "You are a senior technical expert. Based on the task description and context, propose your detailed solution. Requirements: clear structure, executable."

User:
```
## Task
{task}

## Context
{content}

## Scene
{scene}

Please output your detailed proposal.
```

### Review Phase

System: "You are a senior technical reviewer. Review the following proposals objectively, pointing out strengths, weaknesses, and improvement suggestions."

User:
```
## Task
{task}

## Proposals
{proposals_text}

Please provide your review.
```

### Synthesis Phase

System: "You are a senior technical leader. Synthesize the following proposals and reviews into a final, optimal solution. Combine strengths, resolve conflicts, and produce an actionable plan."

User:
```
## Task
{task}

## Original Proposals
{proposals_text}

## Reviews
{reviews_text}

Please output the final consensus plan.
```

## Example

```
User: Use consensus-debate to review this API design

Scene: review
Task: Review the REST API design for user authentication endpoints
Content: 
  POST /auth/login - credentials
  POST /auth/logout - session invalidation  
  GET /auth/me - current user info
  POST /auth/refresh - token refresh

The models will:
1. Each propose their review findings
2. Cross-review each other's analysis
3. Judge synthesizes a comprehensive review with actionable recommendations
```

## Error Handling

- If fewer than 2 models succeed in Phase 1: Raise error (insufficient proposals)
- If a model fails: Log error, continue with remaining models
- If judge model fails: Raise error (cannot synthesize without judge)

## Output Format

Return a structured response containing:

```json
{
  "final_plan": "The synthesized consensus solution...",
  "models_participated": ["model-1", "model-2", "model-3"],
  "models_failed": [],
  "proposals": {
    "model-1": "Proposal from model 1...",
    "model-2": "Proposal from model 2..."
  },
  "reviews": {
    "model-1": "Review from model 1...",
    "model-2": "Review from model 2..."
  }
}
```

## Notes

- All model calls in each phase are concurrent for efficiency
- The skill handles both OpenAI and Anthropic API protocols
- Timeout per model call: 300 seconds (for long reasoning tasks)
- Consider token costs when using "full" review mode with many models
