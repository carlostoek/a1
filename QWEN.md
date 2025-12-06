# Workflow for Implementation Tasks

This document defines the standard workflow to follow when implementing new features or fixing issues in the project.

## Implementation Workflow

When you receive a request for implementation, follow this standardized workflow:

### 1. Develop the Implementation
- Analyze the requirements carefully
- Implement the requested features or fixes
- Follow the existing codebase conventions
- Ensure proper testing of the implementation
- Make sure the code is clean and well-documented internally

### 2. Commit the Implementation
- Stage all the relevant files that were modified
- Create a descriptive commit message that explains what was implemented
- Follow the conventional commit format when possible (feat:, fix:, refactor:, etc.)
- Push the changes to the repository

### 3. Update Documentation Using Specialized Agent
- Use the `telegram-bot-docs` agent to update all relevant documentation
- The agent should update:
  - API documentation (docs/API.md)
  - Architecture documentation (docs/ARCHITECTURE.md)
  - Readme updates (README.md)
  - Changelog entries (docs/CHANGELOG.md)
  - Any other relevant documentation files

### 4. Commit Documentation Updates
- Stage all the updated documentation files
- Create a descriptive commit message for the documentation update
- Push the documentation changes to the repository

## Agent Usage

### telegram-bot-docs Agent
Use this agent for documentation updates with a prompt like:
```
Please update the documentation to include the new feature that has been implemented. Update the API.md, ARCHITECTURE.md, README.md, and CHANGELOG.md files to document:

1. [Describe the new feature/functionality]
2. [API changes or new methods]
3. [Architecture updates]
4. [Configuration changes if any]
5. [Any other relevant documentation updates]
```

### pr-fixes-implementation Agent
Use this agent when implementing fixes from pull request reviews:
```
@agente-fixes PR<number>
```

### telegram-bot-debugger Agent
Use this agent when debugging issues in Telegram bot implementations.

### refactorization-analyst Agent
Use this agent when analyzing and refactoring code systems.

## Commit Message Guidelines

### For Implementation Commits:
- Use imperative mood: "Add feature" not "Added feature"
- Be specific about what was implemented
- Include relevant reference numbers when applicable
- Example: `feat: Add GamificationService with event listener`

### For Documentation Commits:
- Prefix with `docs:`
- Be clear about what documentation was updated
- Example: `docs: Update API documentation for new notification templates`

## Quality Standards

- Each implementation should be self-contained and properly tested
- Documentation should be consistent with existing formats
- Commit messages should be clear and informative
- Follow the project's coding conventions
- Ensure all tests pass before committing
