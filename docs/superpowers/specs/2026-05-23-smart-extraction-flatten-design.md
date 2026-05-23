# Smart Extraction (Flatten) — Design Spec

**Date:** 2026-05-23
**Status:** Draft (Revised)

## Motivation

When archives are created by compressing a parent folder that contains a single subfolder, the resulting archive has redundant intermediate directory levels. For example:

```
project.zip:
  MyProject/              ← top-level (versioned folder name)
    src/                  ← only child, no sibling files
      main.py
      utils/
```

Standard extraction produces `output/MyProject/src/main.py` — the user must navigate two levels deep. Smart extraction with `--flatten` produces `output/MyProject/main.py` — stripping the orphan `src/` middle directory.

## Feature Summary

A new CLI flag `-F` / `--flatten` for the `extract` subcommand. When enabled, the extractor extracts to a temp directory, analyzes the actual directory structure using `Path` API, recursively removes single-child intermediate directories, and moves the result to the output directory.

## Algorithm

### Step 1: Extract to temp directory

```
7z x archive.7z -y [-p<password>] -o<temp_dir>
```

Temp directory created via `tempfile.mkdtemp(dir=output_dir.parent)`.

### Step 2: Compute skip depth from temp directory tree

Walk the temp directory using `Path` methods:

1. `temp_dir` has exactly 1 entry, and it's a directory → step into it (this is the top-level root, always kept).
2. For each deeper level: if the current directory has exactly 1 entry AND it's a directory → increment `skip_depth`, step deeper.
3. If the current directory has != 1 entry, or the single entry is a file → stop.

```
temp_dir/
  A/                ← first level, step in (skip_depth=0)
    B/              ← only child, dir → skip_depth=1, step in
      C1/           ← multiple children → stop
      C2/
```

Result: `skip_depth=1`. Root is at `temp_dir/A`.

### Step 3: Move from temp to output with flattening

```python
# temp_dir contains the extracted tree (e.g., temp_dir/A/B/C1/...)
root_entry = next(temp_dir.iterdir())  # e.g., "A"
if temp_dir has 0 entries:
    return (edge case: empty archive)

if skip_depth > 0:
    # Flatten: walk skip_depth levels deeper to find the chain dir
    chain = root_entry
    for _ in range(skip_depth):
        chain = next(chain.iterdir())  # e.g., A → A/B
    # Move chain's children up to root level
    for child in chain.iterdir():
        shutil.move(str(child), str(root_entry / child.name))
    # Clean up empty intermediate dirs (chain → chain.parent → ... → root)
    current = chain
    while current != root_entry:
        parent = current.parent
        current.rmdir()
        current = parent

# Move content from root_entry into output_dir
output_dir.mkdir(parents=True, exist_ok=True)
for entry in root_entry.iterdir():
    shutil.move(str(entry), str(output_dir / entry.name))
root_entry.rmdir()  # should be empty now
```

### Examples

#### Example 1: Single orphan (standard case)

```
temp_dir/
  MyProject/
    src/
      main.py
      utils.py

Analysis:
  temp_dir → 1 entry: MyProject/ (dir) → step in
  MyProject → 1 entry: src/ (dir) → skip_depth=1, step in
  src → 2 entries: main.py, utils.py (files) → stop

skip_depth = 1

Flatten:
  chain = src/
  Move main.py, utils.py → MyProject/
  Remove empty src/
  Move MyProject/ → output_dir/
  
Result: output_dir/MyProject/main.py, output_dir/MyProject/utils.py
```

#### Example 2: Deep chain

```
temp_dir/
  A/
    B/
      C/
        D/
          file.txt

Analysis:
  temp_dir → A/ (step in)
  A → B/ (skip_depth=1, step in)
  B → C/ (skip_depth=2, step in)
  C → D/ (skip_depth=3, step in)
  D → file.txt (file, not dir) → stop

skip_depth = 3

Flatten:
  chain = D/
  Move file.txt → A/
  Remove D/, C/, B/
  Move A/ → output_dir/
  
Result: output_dir/A/file.txt
```

#### Example 3: No flattening

```
temp_dir/
  MyApp/
    bin/
      app.exe
    doc/
      readme.txt

Analysis:
  temp_dir → MyApp/ (step in)
  MyApp → bin/, doc/ (2 entries) → stop

skip_depth = 0

No flattening. Move MyApp/ → output_dir/

Result: output_dir/MyApp/bin/app.exe, output_dir/MyApp/doc/readme.txt
```

### Edge Cases

| Scenario | Temp structure | Behavior |
|----------|---------------|----------|
| No common root | `file.txt`, `src/file.py` | `temp_dir` has 2 entries → no single root. skip_depth=0, move all to output |
| Root has file + dir | `A/readme.txt`, `A/src/file.py` | `A` has 2 entries → skip_depth=0 |
| Root has multiple dirs | `A/src/`, `A/doc/` | `A` has 2 entries → skip_depth=0 |
| Deep single dir chain | `A/B/C/D/file.txt` | skip_depth=3 → `A/file.txt` |
| Empty archive | `temp_dir` empty | Nothing to move |

## Encryption Handling

When flatten is enabled, the two-phase extraction flow is modified to use a temp directory:

### Without progress bar (`show_progress=False`)
1. Create `temp_dir` via `tempfile.mkdtemp()`
2. `7z x archive -y -o<temp_dir>` with `_try_passwords()` (no progress bar)
3. Analyze `temp_dir` → compute `skip_depth`
4. Reorganize and move from `temp_dir` to `output_dir`
5. `temp_dir.cleanup()` (rmtree)

### With progress bar (`show_progress=True`)
1. **Phase 1**: Create `temp_dir`. Extract to `temp_dir` silently to find password.
2. Analyze `temp_dir` → compute `skip_depth`.
3. Remove `temp_dir`.
4. **Phase 2**: Create new `temp_dir`. Extract to `temp_dir` with progress bar.
5. Reorganize and move from `temp_dir` to `output_dir`.
6. Clean up `temp_dir`.

### Unencrypted archives
1. Create `temp_dir`.
2. `7z x archive -y -o<temp_dir>` (no password).
3. Analyze → reorganize → move to output.
4. Clean up.

## Implementation Plan

### Files Changed

#### `try7z/extractor.py`

- **`_compute_skip_depth(temp_dir: Path) -> int`** — New module-level function. Walks `temp_dir` using `Path.iterdir()` / `Path.is_dir()` to determine how many single-child directory levels to skip. Returns skip count (0 = no flattening).

- **`_flatten_and_move(temp_dir: Path, output_dir: Path, skip_depth: int) -> None`** — New module-level function. 
  1. Finds root entry in `temp_dir`
  2. Walks `skip_depth` levels deeper to find the chain dir
  3. Moves chain's children up to root
  4. Cleans empty intermediate dirs
  5. Moves root's content to `output_dir`

- **`try_extract()`** — Add optional `flatten: bool = False` parameter. When True:
  - Create `temp_dir`
  - Extract to `temp_dir` instead of `output_dir`
  - Call `_compute_skip_depth(temp_dir)` after extraction
  - Call `_flatten_and_move(temp_dir, output_dir, skip_depth)` 
  - Clean up `temp_dir`

- **`extract_with_passwords()`** — Pass through `flatten` parameter.

#### `try7z/cli/main.py`

- **`argparse` extract subparser** — Add `-F` / `--flatten` flag (`action="store_true"`).
- **`_extract_single()`** — Accept and pass `flatten: bool` to `extractor.extract_with_passwords()`.

### Test Plan

#### `tests/test_extractor.py`

- `test_compute_skip_depth_single_child` — Temp with `A/B/C1/file`, `A/B/C2/file` → skip_depth=1
- `test_compute_skip_depth_deep_chain` — Temp with `A/B/C/D/file` → skip_depth=3
- `test_compute_skip_depth_no_common_root` — Temp with `file1`, `dir/file2` → skip_depth=0
- `test_compute_skip_depth_mixed_root` — Temp with `A/file.txt`, `A/B/file.py` → skip_depth=0
- `test_compute_skip_depth_multiple_dirs` — Temp with `A/src/`, `A/doc/` → skip_depth=0
- `test_compute_skip_depth_empty` — Empty temp dir → skip_depth=0
- `test_flatten_and_move` — Create temp structure, call flatten, verify `output_dir` has correct structure
- `test_try_extract_with_flatten` — Integration: encrypted archive with orphan dir → flattened output
- `test_try_extract_flatten_noop` — Archive without orphan dirs → normal structure preserved

### CLI Usage

```bash
# Normal extraction (no flatten)
try7z extract archive.7z

# Smart extraction with flatten
try7z extract archive.7z -F
try7z extract archive.7z --flatten

# With other flags
try7z extract archive.7z -F -p "mypassword" -o ./out
try7z extract archive.7z -F -f    # force overwrite + flatten
```

## Non-Goals

- Does NOT modify the `add` / `remove` / `list` / `clear` password subcommands
- Does NOT add new Python dependencies
- Does NOT change default extraction behavior (flatten is strictly opt-in via `-F`)
- Does NOT handle archives where the extracted tree has a depth greater than what the OS allows
