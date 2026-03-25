# Instruction Module: Create Application Plan

This module guides the AI agent in creating comprehensive application plans from high-level requirements.

## Purpose

Transform a brief feature request or project idea into a detailed, structured application plan that can be broken down into implementable tasks.

## Input

- GitHub Issue with project description
- Any linked reference documents
- Repository context (existing codebase, tech stack)

## Process

1. **Analyze Requirements**
   - Extract key features from issue description
   - Identify stakeholders and users
   - Note any constraints or preferences

2. **Define Architecture**
   - Select appropriate tech stack
   - Design component interactions
   - Identify integration points

3. **Create Breakdown**
   - Decompose into epics/features
   - Estimate complexity
   - Identify dependencies

4. **Document Decisions**
   - Record architectural choices
   - Note alternatives considered
   - Flag risks and mitigations

## Output

A structured application plan document including:
- Executive summary
- Tech stack selection
- Architecture diagram
- Feature breakdown
- Implementation phases
- Risk assessment

## Example Usage

```
/workflow orchestrate-new-project

Issue: Create a user authentication system
```

## Validation

- Plan should be reviewable by stakeholders
- Tasks should be actionable by developers
- Dependencies should be clearly mapped
