# PR Guide: Brand Studio Agent Context Efficiency

## Overview

This PR implements context efficiency improvements for the Brand Studio advisor agent. The goal is to reduce context window consumption by AI agents through pagination, chunking, and summarization of tool outputs.

## Task List Reference

See `TODO_CONTEXT_EFFICIENCY.md` for the complete task list.

## Completed Tasks

### Task 1: Add Pagination to `list_files()` ✅

**Commit:** `c80f631` - feat(advisor): Add pagination to list_files() tool

**Changes:**
- `src/sip_videogen/advisor/tools.py`:
  - Added `limit` and `offset` parameters to `_impl_list_files()`
  - Default limit: 20 items, max: 100 items
  - Shows pagination info (e.g., "showing 1-20 of 85")
  - Adds hint for next page when more items available
  - Validates parameters: resets negative values, caps limit at 100
  - Returns error when offset is past end of directory

- `tests/test_advisor_tools.py`:
  - Added 6 new tests for pagination functionality
  - Tests cover: default limit, offset, custom limit, offset past end, invalid params, small dirs

**Verification:**
- All 24 tests pass
- Ruff check passes
- Code formatted with ruff

### Task 2: Add Chunking to `read_file()` ✅

**Commit:** `2c369e2` - feat(advisor): Add chunking to read_file() tool

**Changes:**
- `src/sip_videogen/advisor/tools.py`:
  - Added `chunk` and `chunk_size` parameters to `_impl_read_file()`
  - Default chunk_size: 2000 chars, min: 100, max: 10000
  - Small files (< chunk_size) returned as-is without metadata
  - Large files return requested chunk with position info (e.g., "[Chunk 1/3] (chars 1-2000 of 5000)")
  - Includes hint for reading next chunk when more available
  - Validates chunk parameter: error for negative or out of range

- `tests/test_advisor_tools.py`:
  - Added 8 new tests for chunking functionality:
    - `test_read_large_file_chunked`
    - `test_read_file_second_chunk`
    - `test_read_file_last_chunk`
    - `test_read_file_invalid_chunk`
    - `test_read_file_negative_chunk`
    - `test_read_small_file_no_chunking`
    - `test_read_file_custom_chunk_size`
    - `test_read_file_chunk_size_validation`

**Verification:**
- All 32 tests pass
- Ruff check passes
- Code formatted with ruff

### Task 3: Add Summary Mode to `load_brand()` ✅

**Commit:** `1075be8` - feat(advisor): Add summary mode to load_brand() tool

**Changes:**
- `src/sip_videogen/advisor/tools.py`:
  - Added `detail_level: Literal["summary", "full"]` parameter (default: "summary")
  - Summary mode (~500 chars): name, tagline, category, tone, colors (max 3), style (max 3), audience, asset count
  - Full mode (~2000 chars): preserves existing complete output
  - Summary includes hint: "use `load_brand(detail_level='full')` for complete details"
  - Updated both `_impl_load_brand()` and wrapper `load_brand()` functions

**Verification:**
- 31/32 advisor tools tests pass
- 1 expected failure: `test_load_brand_includes_assets_section` (will be fixed in Task 5)
- Ruff check passes
- Summary mode: ~479 chars, Full mode: ~1018+ chars (verified)

### Task 4: Update Code That Expects Full load_brand Output ✅

**Commit:** `8d05235` - docs(advisor): Update references to reflect load_brand() default summary mode

**Changes:**
- `src/sip_videogen/advisor/prompts/advisor.md`:
  - Updated line 30 tool description to clarify summary is default
  - Updated Brand Context section (lines 137-144) to explain summary vs full modes

- `src/sip_videogen/advisor/agent.py`:
  - Updated default prompt tool description (line 264)
  - Updated brand context hint (lines 231-234)

- `src/sip_videogen/advisor/skills/brand_evolution/SKILL.md`:
  - Updated prerequisite to use `load_brand(detail_level='full')` since evolution needs full context

**Verification:**
- 31/32 advisor tools tests pass (same as before)
- 1 expected failure remains: `test_load_brand_includes_assets_section` (will be fixed in Task 5)
- Ruff check passes (1 pre-existing line length warning on unrelated line)

### Task 5: Update Existing Tests for load_brand Changes ✅

**Commit:** `e887baf` - test(advisor): Update load_brand tests for summary mode default

**Changes:**
- `tests/test_advisor_tools.py`:
  - Replaced `test_load_brand_includes_assets_section` with new tests:
    - `test_load_brand_summary_mode_default`: verifies summary is default mode
    - `test_load_brand_full_mode`: verifies full mode includes all sections
    - `test_load_brand_summary_character_count`: verifies summary is ~500 chars
  - Added `_create_mock_identity()` helper method to reduce test code duplication
  - Summary mode tests verify: name, tagline, category, tone, colors, asset count
  - Full mode tests verify: ## Available Assets section is present

**Verification:**
- All 34 tests pass
- Ruff check passes
- Code formatted with ruff

## Remaining Tasks

### Stage 1: Tool Result Summarization
- [x] Task 3: Add summary mode to `load_brand()` tool
- [x] Task 4: Update code that expects full load_brand output
- [x] Task 5: Update existing tests for load_brand changes

### Stage 2: Token-Aware History Management
- [ ] Task 6: Create history manager module
- [ ] Task 7: Integrate history manager into agent

### Stage 3: Context Budget Guard
- [ ] Task 8: Create context budget module
- [ ] Task 9: Integrate budget guard into agent

## Testing

```bash
# Run all advisor tools tests
python -m pytest tests/test_advisor_tools.py -v

# Run specific pagination tests
python -m pytest tests/test_advisor_tools.py -k "pagination" -v

# Run linting
ruff check src/sip_videogen/advisor/tools.py
```

## Notes

- The `list_files()` tool now returns paginated results by default (20 items)
- Small directories (<= 20 items) do not show pagination info
- The agent can use `offset` parameter to navigate through large directories
- The `read_file()` tool now chunks large files (> 2000 chars) by default
- Small files are returned as-is without chunking metadata
- The agent can use `chunk` parameter to navigate through large files
- The `load_brand()` tool now returns summary by default (~500 chars)
- Use `detail_level='full'` for complete brand context (~2000 chars)
- Summary mode reduces context consumption by ~75% for routine brand loads
