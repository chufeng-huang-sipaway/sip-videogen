# PR Guide: sip-videogen Development

## Overview
This PR implements the sip-videogen CLI tool that transforms vague video ideas into complete videos using an AI agent team.

## Current Progress

### Completed Tasks
- [x] **Task 1.1: Initialize Project Structure**
  - Created `pyproject.toml` with all dependencies
  - Directory structure: `src/sip_videogen/` with subfolders (agents, generators, models, config, assembler, storage)
  - `__init__.py` files in all packages
  - `__main__.py` for `python -m sip_videogen` execution
  - `.env.example` with all required environment variables
  - `.gitignore` for Python projects
  - Placeholder `cli.py` with Typer app

### Pending Tasks
- [ ] Task 1.2: Implement Configuration with Pydantic Settings
- [ ] Task 1.3: Create CLI Skeleton with Typer
- [ ] Task 1.4: Set Up Logging with Rich
- [ ] Task 2.1: Implement Core Script Models
- [ ] Task 2.2: Implement Asset and Production Models
- [ ] Task 2.3: Implement Agent Output Models
- [ ] Task 3.1-3.4: Agent Team Implementation
- [ ] Task 4.1-4.2: Image Generation
- [ ] Task 5.1-5.3: Video Generation
- [ ] Task 6.1: FFmpeg Wrapper
- [ ] Task 7.1-7.4: Integration and Polish

## Project Structure
```
sip-videogen/
├── pyproject.toml
├── .env.example
├── .gitignore
├── src/
│   └── sip_videogen/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── agents/
│       │   ├── __init__.py
│       │   └── prompts/
│       │       └── __init__.py
│       ├── assembler/
│       │   └── __init__.py
│       ├── config/
│       │   └── __init__.py
│       ├── generators/
│       │   └── __init__.py
│       ├── models/
│       │   └── __init__.py
│       └── storage/
│           └── __init__.py
└── tests/
    └── __init__.py
```

## How to Continue
1. Read `TASKS.md` for detailed task specifications
2. The next task is **Task 1.2: Implement Configuration with Pydantic Settings**
3. Follow the implementation hints in the task description

## Testing
```bash
# Install in development mode
pip install -e ".[dev]"

# Run the CLI
sip-videogen --help
```
