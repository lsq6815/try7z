# Smart Extraction (Flatten) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `-F`/`--flatten` flag to `try7z extract` that recursively strips single-child intermediate directories from extracted archive paths.

**Architecture:** Two new module-level functions in `try7z/extractor.py` (`_compute_skip_depth`, `_flatten_and_move`), a new `_flatten_extract` helper method on `Extractor`, a small modification to `try_extract` to route to it when `flatten=True`, and CLI plumbing in `try7z/cli/main.py`.

**Tech Stack:** Python 3.10+, pathlib, shutil, tempfile, pytest

---

## File Map

| File | Responsibility | Change |
|------|---------------|--------|
| `try7z/extractor.py` | New helper functions + flatten routing in `try_extract` | Add `import tempfile`, `_compute_skip_depth()`, `_flatten_and_move()`, `_flatten_extract()`, modify `try_extract()`, modify `extract_with_passwords()` |
| `try7z/cli/main.py` | CLI flag + pass-through | Add `-F`/`--flatten` arg, pass `flatten` through `_extract_single` |
| `tests/test_extractor.py` | Unit + integration tests | Add `TestComputeSkipDepth`, `TestFlattenAndMove`, add flatten tests to `TestExtractor` |

---

### Task 1: `_compute_skip_depth` function

**Files:**
- Create: (none — added to existing file)
- Modify: `try7z/extractor.py` (add function after `get_7z_version`)
- Test: `tests/test_extractor.py` (add new test class)

- [ ] **Step 1: Write failing tests for `_compute_skip_depth`**

```python
from try7z.extractor import _compute_skip_depth


class TestComputeSkipDepth:
    """Tests for _compute_skip_depth."""

    def test_empty_dir(self, temp_dir: Path) -> None:
        """Empty temp dir returns 0."""
        assert _compute_skip_depth(temp_dir) == 0

    def test_multiple_root_entries(self, temp_dir: Path) -> None:
        """Multiple entries at root returns 0."""
        (temp_dir / "file1.txt").write_text("")
        (temp_dir / "dir1").mkdir()
        assert _compute_skip_depth(temp_dir) == 0

    def test_single_root_file(self, temp_dir: Path) -> None:
        """Single file at root returns 0."""
        (temp_dir / "readme.txt").write_text("")
        assert _compute_skip_depth(temp_dir) == 0

    def test_single_child_dir(self, temp_dir: Path) -> None:
        """Single orphan subdir returns 1."""
        root = temp_dir / "A"
        root.mkdir()
        orphan = root / "B"
        orphan.mkdir()
        (orphan / "C1").mkdir()
        (orphan / "C2").mkdir()
        assert _compute_skip_depth(temp_dir) == 1

    def test_deep_chain(self, temp_dir: Path) -> None:
        """Deep single-child chain returns correct depth."""
        chain = temp_dir / "A" / "B" / "C" / "D"
        chain.mkdir(parents=True)
        (chain / "file.txt").write_text("")
        assert _compute_skip_depth(temp_dir) == 3  # skip B, C, D

    def test_multiple_dirs_at_second_level(self, temp_dir: Path) -> None:
        """Root with multiple subdirs returns 0."""
        root = temp_dir / "A"
        root.mkdir()
        (root / "src").mkdir()
        (root / "doc").mkdir()
        assert _compute_skip_depth(temp_dir) == 0

    def test_mixed_file_and_dir_at_second_level(self, temp_dir: Path) -> None:
        """Root with file + dir returns 0."""
        root = temp_dir / "A"
        root.mkdir()
        (root / "readme.txt").write_text("")
        (root / "src").mkdir()
        (root / "src" / "main.py").write_text("")
        assert _compute_skip_depth(temp_dir) == 0

    def test_no_common_root(self, temp_dir: Path) -> None:
        """No single root entry returns 0."""
        (temp_dir / "file.txt").write_text("")
        (temp_dir / "dir").mkdir()
        assert _compute_skip_depth(temp_dir) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_extractor.py::TestComputeSkipDepth -v
```
Expected: All tests FAIL with `ImportError` (function not yet defined).

- [ ] **Step 3: Implement `_compute_skip_depth` in `try7z/extractor.py`**

Add after the `get_7z_version()` function (line 121):

```python
def _compute_skip_depth(temp_dir: Path) -> int:
    """Count single-child directory levels between root and first branch.

    Walks the extracted temp directory tree using pathlib. The first
    entry in temp_dir is considered the archive root and is always
    kept. Each subsequent level that contains exactly one directory
    (no files, no siblings) increments the skip count. Stops at the
    first level with multiple entries or a file.

    Args:
        temp_dir: Path to the directory containing extracted archive contents.

    Returns:
        Number of single-child directory levels to skip (0 = no flattening).

    Example:
        temp_dir/
          A/           <- root, kept
            B/         <- single child dir -> skip
              C1/      <- multiple entries -> stop
              C2/
        Returns 1 (skip B).
    """
    entries = list(temp_dir.iterdir())
    if len(entries) != 1:
        return 0
    current = entries[0]
    if not current.is_dir():
        return 0

    skip_depth = 0
    while True:
        sub_entries = list(current.iterdir())
        if len(sub_entries) != 1:
            break
        child = sub_entries[0]
        if not child.is_dir():
            break
        skip_depth += 1
        current = child

    return skip_depth
```

Add to the module-level exports (it will be imported in tests): verify `__all__` if present, otherwise it's fine as a public function.

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_extractor.py::TestComputeSkipDepth -v
```
Expected: All 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add try7z/extractor.py tests/test_extractor.py
git commit -m "feat: add _compute_skip_depth function with tests"
```

---

### Task 2: `_flatten_and_move` function

**Files:**
- Modify: `try7z/extractor.py` (add function)
- Test: `tests/test_extractor.py` (add test class)

- [ ] **Step 1: Write failing tests for `_flatten_and_move`**

```python
from try7z.extractor import _flatten_and_move


class TestFlattenAndMove:
    """Tests for _flatten_and_move."""

    def test_no_flattening_single_root(self, temp_dir: Path) -> None:
        """skip_depth=0 moves root contents to output."""
        src = temp_dir / "src"
        src.mkdir()
        root = src / "MyApp"
        root.mkdir()
        (root / "main.py").write_text("code")
        (root / "doc").mkdir()
        (root / "doc" / "readme.txt").write_text("docs")

        output = temp_dir / "out"

        _flatten_and_move(src, output, skip_depth=0)

        assert output.is_dir()
        assert (output / "MyApp" / "main.py").exists()
        assert (output / "MyApp" / "doc" / "readme.txt").exists()
        assert not src.exists() or not any(src.iterdir())

    def test_flatten_single_level(self, temp_dir: Path) -> None:
        """skip_depth=1 moves orphan's children up to root."""
        src = temp_dir / "src"
        src.mkdir()
        root = src / "MyProject"
        root.mkdir()
        orphan = root / "src"
        orphan.mkdir()
        (orphan / "main.py").write_text("code")
        (orphan / "utils.py").write_text("helpers")

        output = temp_dir / "out"

        _flatten_and_move(src, output, skip_depth=1)

        assert output.is_dir()
        assert (output / "MyProject" / "main.py").exists()
        assert (output / "MyProject" / "utils.py").exists()
        assert not (output / "MyProject" / "src").exists()

    def test_flatten_deep_chain(self, temp_dir: Path) -> None:
        """skip_depth=3 flattens deep single-child chain."""
        src = temp_dir / "src"
        src.mkdir()
        root = src / "A"
        root.mkdir()
        chain = root / "B" / "C" / "D"
        chain.mkdir(parents=True)
        (chain / "file.txt").write_text("deep")

        output = temp_dir / "out"

        _flatten_and_move(src, output, skip_depth=3)

        assert output.is_dir()
        assert (output / "A" / "file.txt").exists()
        assert not (output / "A" / "B").exists()

    def test_empty_temp_dir(self, temp_dir: Path) -> None:
        """Empty temp dir creates empty output dir."""
        src = temp_dir / "src"
        src.mkdir()
        output = temp_dir / "out"

        _flatten_and_move(src, output, skip_depth=0)

        assert output.is_dir()

    def test_flatten_preserves_sibling_dirs(self, temp_dir: Path) -> None:
        """Multiple dirs under orphan are moved together."""
        src = temp_dir / "src"
        src.mkdir()
        root = src / "App"
        root.mkdir()
        orphan = root / "lib"
        orphan.mkdir()
        (orphan / "foo").mkdir()
        (orphan / "bar").mkdir()
        (orphan / "foo" / "f.py").write_text("f")
        (orphan / "bar" / "b.py").write_text("b")

        output = temp_dir / "out"

        _flatten_and_move(src, output, skip_depth=1)

        assert output.is_dir()
        assert (output / "App" / "foo" / "f.py").exists()
        assert (output / "App" / "bar" / "b.py").exists()
        assert not (output / "App" / "lib").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_extractor.py::TestFlattenAndMove -v
```
Expected: All tests FAIL with `ImportError`.

- [ ] **Step 3: Implement `_flatten_and_move` in `try7z/extractor.py`**

Add after `_compute_skip_depth`:

```python
def _flatten_and_move(temp_dir: Path, output_dir: Path, skip_depth: int) -> None:
    """Reorganize extracted tree and move to output directory.

    Reads the extracted tree from temp_dir, optionally flattens
    skip_depth single-child directory levels, and moves the result
    to output_dir.

    Args:
        temp_dir: Directory containing the extracted archive tree.
        output_dir: Target directory for the (possibly flattened) output.
        skip_depth: Number of single-child dir levels to remove.
                   0 means no flattening (just move root contents).
    """
    entries = list(temp_dir.iterdir())
    if not entries:
        output_dir.mkdir(parents=True, exist_ok=True)
        return

    root_entry = entries[0]

    if skip_depth > 0:
        chain = root_entry
        for _ in range(skip_depth):
            chain = next(chain.iterdir())

        for child in list(chain.iterdir()):
            target = root_entry / child.name
            shutil.move(str(child), str(target))

        current = chain
        while current != root_entry:
            parent = current.parent
            current.rmdir()
            current = parent

    output_dir.mkdir(parents=True, exist_ok=True)
    for entry in list(root_entry.iterdir()):
        shutil.move(str(entry), str(output_dir / entry.name))
    root_entry.rmdir()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_extractor.py::TestFlattenAndMove -v
```
Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add try7z/extractor.py tests/test_extractor.py
git commit -m "feat: add _flatten_and_move function with tests"
```

---

### Task 3: `_flatten_extract` helper + `try_extract` routing

**Files:**
- Modify: `try7z/extractor.py` (add method, modify `try_extract`, modify `extract_with_passwords`)

- [ ] **Step 1: Add `import tempfile` to `try7z/extractor.py`**

Add `import tempfile` to the imports block (after line 44 `from pathlib import Path`).

- [ ] **Step 2: Add `_flatten_extract` method to `Extractor` class (before `extract_with_passwords`)**

Add after `_try_passwords` method (after line 259) and before `try_extract` (line 261):

```python
    def _flatten_extract(
        self,
        output_dir: Path,
        passwords_to_try: list[str | None],
        show_progress: bool,
        show_password_progress: bool,
    ) -> tuple[bool, str | None]:
        """Extract to temp dir, flatten, then move to output.

        Args:
            output_dir: Final output directory for flattened content.
            passwords_to_try: Password list (None = no password).
            show_progress: Whether to show tqdm progress bar.
            show_password_progress: Whether to show password attempt counter.

        Returns:
            Tuple of (success, used_password).
        """
        temp_dir = Path(tempfile.mkdtemp(dir=output_dir.parent))

        try:
            if show_progress:
                found, pwd, attempts = self._try_passwords(
                    temp_dir, passwords_to_try, show_password_progress
                )
                if not found:
                    if show_password_progress:
                        print()
                    return False, None

                if show_password_progress:
                    print(f"\nFound after {attempts} trie(s)!")

                skip_depth = _compute_skip_depth(temp_dir)
                shutil.rmtree(temp_dir)

                temp_dir2 = Path(tempfile.mkdtemp(dir=output_dir.parent))
                try:
                    success = self._extract_with_password(
                        temp_dir2, pwd, show_progress=True
                    )
                    if success:
                        _flatten_and_move(temp_dir2, output_dir, skip_depth)
                        return True, pwd
                    return False, None
                finally:
                    if temp_dir2.exists():
                        shutil.rmtree(temp_dir2, ignore_errors=True)
            else:
                success, pwd, _ = self._try_passwords(
                    temp_dir, passwords_to_try, show_password_progress
                )
                if success:
                    skip_depth = _compute_skip_depth(temp_dir)
                    _flatten_and_move(temp_dir, output_dir, skip_depth)
                    return True, pwd
                return False, None
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
```

- [ ] **Step 3: Modify `try_extract` to route flatten requests**

In `try_extract()` (starts at line 261), add `flatten: bool = False` parameter and an early-return branch at the top of the method body (after `passwords_to_try` assignment):

```python
    def try_extract(
        self,
        output_dir: Path | None = None,
        passwords: list[str] | None = None,
        show_progress: bool = False,
        show_password_progress: bool = False,
        flatten: bool = False,
    ) -> tuple[bool, str | None]:
```

Insert after the `passwords_to_try = ...` line (current line 325):

```python
        if flatten:
            if output_dir is None:
                output_dir = self.archive_path.parent / self.archive_path.stem
            output_dir = output_dir.resolve()
            return self._flatten_extract(
                output_dir, passwords_to_try, show_progress, show_password_progress
            )
```

- [ ] **Step 4: Modify `extract_with_passwords` to pass `flatten`**

In `extract_with_passwords()` (starts at line 569), add `flatten: bool = False` parameter and pass it to `try_extract`:

```python
    def extract_with_passwords(
        self,
        passwords: list[str],
        output_dir: Path | None = None,
        show_progress: bool = False,
        show_password_progress: bool = False,
        flatten: bool = False,
    ) -> tuple[bool, str | None]:
```

And in the call to `try_extract` (line 616-618):

```python
        success, used_password = self.try_extract(
            output_dir, passwords, show_progress, show_password_progress, flatten
        )
```

- [ ] **Step 5: Run existing tests to ensure no regressions**

```bash
pytest tests/test_extractor.py -v --timeout=120
```
Expected: All existing tests PASS (7z binary calls still work).

- [ ] **Step 6: Commit**

```bash
git add try7z/extractor.py
git commit -m "feat: add flatten parameter to try_extract and extract_with_passwords"
```

---

### Task 4: CLI integration

**Files:**
- Modify: `try7z/cli/main.py`

- [ ] **Step 1: Add `-F`/`--flatten` argument to extract subparser**

After the `--force` argument (line 880), add:

```python
    extract_parser.add_argument(
        "-F",
        "--flatten",
        action="store_true",
        help="Flatten single-child intermediate directories in extracted output",
    )
```

- [ ] **Step 2: Accept and pass `flatten` in `_extract_single`**

Add `flatten: bool` parameter to `_extract_single` (line 626):

```python
def _extract_single(
    archive_path: Path,
    output_dir: Path,
    passwords: list[str],
    force: bool,
    flatten: bool = False,
) -> int:
```

Pass it to `extractor.extract_with_passwords()` (line 646-648):

```python
        success, used_password = extractor.extract_with_passwords(
            passwords, output_dir, show_progress=True, show_password_progress=True,
            flatten=flatten,
        )
```

- [ ] **Step 3: Pass `flatten` from `cmd_extract` to `_extract_single`**

In `cmd_extract` at line 730, change:

```python
        result = _extract_single(archive_path, output_dir, passwords, args.force)
```

to:

```python
        result = _extract_single(archive_path, output_dir, passwords, args.force, flatten=args.flatten)
```

- [ ] **Step 4: Update `cmd_extract` docstring to document `--flatten`**

Update the args documentation to include `flatten`.

- [ ] **Step 5: Run tests to verify CLI parsing**

```bash
python -c "from try7z.cli.main import main; import sys; sys.argv = ['try7z', 'extract', 'test.7z', '-F']; print('CLI parses OK')"
```

Expected: "CLI parses OK" (no argparse error).

- [ ] **Step 6: Commit**

```bash
git add try7z/cli/main.py
git commit -m "feat: add -F/--flatten CLI flag for smart extraction"
```

---

### Task 5: Integration tests for flatten extraction

**Files:**
- Test: `tests/test_extractor.py` (add to `TestExtractor` class)

- [ ] **Step 1: Add integration test fixture for nested archive**

Add a new fixture in `test_extractor.py` for an archive with a single orphan directory:

```python
@pytest.fixture
def nested_orphan_archive(temp_dir: Path, seven_zip: Path) -> Path:
    """Create a 7z archive where src/ contains only one subdir: nested/.
    
    Structure inside archive:
      MyProject/
        nested/
          main.py
          utils.py
    """
    src = temp_dir / "src"
    proj = src / "MyProject"
    nested = proj / "nested"
    nested.mkdir(parents=True)
    (nested / "main.py").write_text("print('hello')")
    (nested / "utils.py").write_text("helpers")

    archive_path = temp_dir / "nested_orphan.7z"
    subprocess.run(
        [str(seven_zip), "a", str(archive_path), str(src)],
        capture_output=True,
        check=True,
    )
    return archive_path


@pytest.fixture
def deep_chain_archive(temp_dir: Path, seven_zip: Path) -> Path:
    """Create archive with deep single-child directory chain.
    
    Structure inside archive:
      src/A/B/C/D/file.txt
    """
    src = temp_dir / "src"
    chain = src / "A" / "B" / "C" / "D"
    chain.mkdir(parents=True)
    (chain / "file.txt").write_text("deep content")

    archive_path = temp_dir / "deep_chain.7z"
    subprocess.run(
        [str(seven_zip), "a", str(archive_path), str(src)],
        capture_output=True,
        check=True,
    )
    return archive_path


@pytest.fixture
def multi_dir_archive(temp_dir: Path, seven_zip: Path) -> Path:
    """Create archive with multiple top-level subdirs (no flattening needed).
    
    Structure inside archive:
      src/MyApp/bin/app.exe
      src/MyApp/doc/readme.txt
    """
    src = temp_dir / "src"
    app = src / "MyApp"
    (app / "bin").mkdir(parents=True)
    (app / "doc").mkdir(parents=True)
    (app / "bin" / "app.exe").write_text("binary")
    (app / "doc" / "readme.txt").write_text("docs")

    archive_path = temp_dir / "multi_dir.7z"
    subprocess.run(
        [str(seven_zip), "a", str(archive_path), str(src)],
        capture_output=True,
        check=True,
    )
    return archive_path
```

- [ ] **Step 2: Add integration test methods to `TestExtractor`**

```python
    def test_flatten_single_orphan(
        self, nested_orphan_archive: Path, temp_dir: Path
    ) -> None:
        """Flatten removes single orphan directory level."""
        extractor = Extractor(nested_orphan_archive)
        output_dir = temp_dir / "output"

        success, password = extractor.try_extract(
            output_dir, flatten=True
        )

        assert success is True
        assert password is None
        assert (output_dir / "MyProject" / "main.py").exists()
        assert (output_dir / "MyProject" / "utils.py").exists()
        assert not (output_dir / "MyProject" / "nested").exists()

    def test_flatten_deep_chain(
        self, deep_chain_archive: Path, temp_dir: Path
    ) -> None:
        """Flatten removes all single-child intermediate dirs."""
        extractor = Extractor(deep_chain_archive)
        output_dir = temp_dir / "output"

        success, password = extractor.try_extract(
            output_dir, flatten=True
        )

        assert success is True
        assert password is None
        assert (output_dir / "A" / "file.txt").exists()
        assert not (output_dir / "A" / "B").exists()

    def test_flatten_noop_multiple_dirs(
        self, multi_dir_archive: Path, temp_dir: Path
    ) -> None:
        """No flattening when root has multiple subdirs (normal structure preserved)."""
        extractor = Extractor(multi_dir_archive)
        output_dir = temp_dir / "output"

        success, password = extractor.try_extract(
            output_dir, flatten=True
        )

        assert success is True
        assert password is None
        assert (output_dir / "MyApp" / "bin" / "app.exe").exists()
        assert (output_dir / "MyApp" / "doc" / "readme.txt").exists()
```

- [ ] **Step 3: Run integration tests**

```bash
pytest tests/test_extractor.py::TestExtractor::test_flatten_single_orphan tests/test_extractor.py::TestExtractor::test_flatten_deep_chain tests/test_extractor.py::TestExtractor::test_flatten_noop_multiple_dirs -v --timeout=120
```
Expected: All 3 PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_extractor.py
git commit -m "test: add integration tests for flatten extraction"
```

---

### Task 6: Final verification

**Files:**
- (no changes, verification only)

- [ ] **Step 1: Run full test suite**

```bash
pytest -m "not benchmark" --timeout=120 -v
```
Expected: All non-benchmark tests PASS.

- [ ] **Step 2: Run linting**

```bash
ruff check .
```
Expected: No errors.

- [ ] **Step 3: Run type checking**

```bash
mypy try7z/
```
Expected: No errors.

- [ ] **Step 4: Commit any lint/type fixes (if needed)**

Only if changes were required.

---

### Task 7: End-to-end manual smoke test

- [ ] **Step 1: Create a test archive with nested orphan structure**

```bash
mkdir "$env:TEMP\flatten_test\src\MyProject\nested" -Force
echo "hello" > "$env:TEMP\flatten_test\src\MyProject\nested\main.py"
echo "world" > "$env:TEMP\flatten_test\src\MyProject\nested\utils.py"
& (Get-Command 7z.exe).Source a "$env:TEMP\flatten_test\test.7z" "$env:TEMP\flatten_test\src"
```

- [ ] **Step 2: Extract with flatten flag**

```bash
python -m try7z extract "$env:TEMP\flatten_test\test.7z" -F -o "$env:TEMP\flatten_test\out"
```
Expected: Output contains `MyProject/main.py` and `MyProject/utils.py` (NOT `MyProject/nested/main.py`).

- [ ] **Step 3: Verify output structure**

```bash
Get-ChildItem -Recurse "$env:TEMP\flatten_test\out" | ForEach-Object { $_.FullName }
```
Expected:
```
...\out\MyProject
...\out\MyProject\main.py
...\out\MyProject\utils.py
```

- [ ] **Step 4: Clean up**

```bash
Remove-Item -Recurse -Force "$env:TEMP\flatten_test"
```
