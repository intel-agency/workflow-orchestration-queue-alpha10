# Instruction Module: Analyze Bug

This module guides the AI agent in analyzing and fixing bugs.

## Purpose

Take a bug report, analyze the root cause, and implement a fix.

## Input

- GitHub Issue with bug description
- Stack traces or error logs
- Steps to reproduce

## Process

1. **Reproduce**
   - Understand the reported behavior
   - Attempt to reproduce locally
   - Document reproduction steps

2. **Analyze**
   - Review relevant code paths
   - Identify root cause
   - Determine impact scope

3. **Plan Fix**
   - Design minimal fix
   - Consider side effects
   - Plan test coverage

4. **Implement**
   - Apply fix
   - Add regression test
   - Update documentation if needed

5. **Validate**
   - Verify fix resolves issue
   - Run all tests
   - Check for regressions

## Output

- Bug fix in a Pull Request
- Regression test
- Issue comment explaining the fix

## Example Usage

```
/workflow fix-bug

Issue: Login fails with special characters in password
Error: ValueError: Invalid character in password field
```

## Quality Gates

- Bug is reproducible before fix
- Bug is not reproducible after fix
- Regression test added
- No new test failures
