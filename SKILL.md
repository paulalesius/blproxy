# Testing

## Run all tests

```bash
cd /src/exrouter
./test.sh
```

Or from anywhere:

```bash
bash /src/exrouter/test.sh
```

## What test.sh does

1. `uv sync --all-extras` - Install all dependencies
2. `uv run pytest tests/ -v` - Run all 36 tests

## Expected result

```
======================== 36 passed, 3 warnings in 7.30s ========================
```

## Test file structure

- `tests/test_backend.py` - Backend matching (4 tests)
- `tests/test_config.py` - Configuration (3 tests)
- `tests/test_hooks.py` - Hook mechanism (7 tests)
- `tests/test_lock_manager.py` - Lock management (7 tests)
- `tests/test_proxy.py` - Proxy routing (8 tests)
- `tests/test_pydantic_validation.py` - Pydantic validation (5 tests)
- `tests/test_tei_embedding_remapper.py` - TEI embedding remapper (2 tests)
- `tests/test_reranker_remapper.py` - TEI reranker remapper (3 tests)

## Remapper tests

Remapper tests use mocked HTTP responses based on exact data from live backends:

- Embedding backend (8081): Returns `{"model": "...", "data": [{"embedding": [...1024...], "index": 0}]}`
- Reranker backend (8082): Returns `{"model": "...", "results": [{"index": 0, "relevance_score": -3.71...}]}`
- Mocks truncate embeddings to `[0.0] * 1024` for cleaner test data

### Format tests

Embedding remapper handles two formats based on path:

- `/embed` → returns list `[embedding1, embedding2, ...]` (raw TEI format)
- `/embeddings` → returns dict `{"data": [{"embedding": [...], "index": 0}]}` (OpenAI format)

Reranker remapper normalizes paths and handles `texts` → `documents` conversion.

## If tests fail

1. Check that `uv` is in PATH
2. Make sure `tests/` directory exists
3. Run `uv sync` manually if dependencies are missing
4. Use `--project /src/exrouter` if running pytest outside the directory

## Git commits

After all tests pass, you can commit the changes:

```bash
cd /src/exrouter
git add tests/
git commit -m "Describe your change"
```

**Important:** Do NOT commit until the user has approved the changes. Show git status and wait for explicit "commit" or "approved" before running `git commit`.
