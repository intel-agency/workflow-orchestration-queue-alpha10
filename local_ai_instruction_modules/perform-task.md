# Instruction Module: Perform Task

This module guides the AI agent in implementing a specific task from the backlog.

## Purpose

Take a well-defined task and implement it end-to-end, including code changes, tests, and documentation.

## Input

- GitHub Issue with task description
- Related application plan (if applicable)
- Codebase context

## Process

1. **Understand Context**
   - Read task requirements carefully
   - Review related code
   - Check existing patterns

2. **Plan Implementation**
   - Identify files to modify
   - Design approach
   - Consider edge cases

3. **Implement**
   - Write code following project conventions
   - Add/update tests
   - Update documentation

4. **Validate**
   - Run existing tests
   - Run new tests
   - Check linting/formatting

5. **Submit**
   - Create feature branch
   - Commit with descriptive message
   - Create Pull Request

## Output

- Code changes in a Pull Request
- Updated tests
- Updated documentation
- PR description linking to issue

## Example Usage

```
/workflow perform-task

Issue: Add password reset functionality
```

## Quality Gates

- All tests pass
- Code coverage maintained
- Linting passes
- Documentation updated
