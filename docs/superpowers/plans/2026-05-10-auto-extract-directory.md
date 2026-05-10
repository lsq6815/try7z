# try7z extract 目录自动解压功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `try7z extract` 命令添加目录输入支持，自动扫描目录下支持的压缩包并逐个解压。

**Architecture:** 在 `main.py` 中新增 `_resolve_input_paths` 路径解析函数，将混合的文件/目录输入统一解析为压缩包文件列表。`cmd_extract` 在开头调用此函数，其余逻辑保持不变。

**Tech Stack:** Python 3.10+, pytest, pathlib

---

## 文件结构

| 文件 | 操作 | 说明 |
|------|------|------|
| `try7z/main.py` | 修改 | 新增 `_resolve_input_paths` 函数（约 60 行），修改 `cmd_extract` 函数（约 5 行） |
| `tests/test_cli.py` | 修改 | 新增 `TestResolveInputPaths` 测试类（约 120 行），新增目录解压集成测试 |

---

## Task 1: 新增 `_resolve_input_paths` 函数

**Files:**
- Modify: `try7z/main.py`（在 `_build_password_list` 函数之后、`_resolve_output_dir` 之前插入）

- [ ] **Step 1: 导入 `is_supported_archive`**

在 `try7z/main.py` 的 imports 区域，确保 `is_supported_archive` 已被导入：

```python
from try7z.utils import (
    # ... 其他导入 ...
    is_supported_archive,
    # ... 其他导入 ...
)
```

检查现有导入，如果已导入则跳过此步骤。

- [ ] **Step 2: 编写 `_resolve_input_paths` 函数**

在 `_build_password_list` 函数之后（约第 503 行）、`_resolve_output_dir` 之前插入：

```python
def _resolve_input_paths(paths: list[str]) -> list[Path]:
    """Resolve input paths to a list of supported archive files.

    For each path in the input list:
    - If it's a supported archive file (.7z/.zip/.rar), include it
    - If it's a directory, scan non-recursively for supported archives
    - If it's neither, print a warning and skip
    - If the path doesn't exist, print a warning and skip

    Args:
        paths: List of input paths (files or directories).

    Returns:
        Sorted list of absolute paths to archive files.

    Example:
        >>> from pathlib import Path
        >>> from try7z.main import _resolve_input_paths
        >>> # Single file
        >>> result = _resolve_input_paths(["archive.7z"])
        >>> len(result)
        1
        >>> # Directory with archives
        >>> result = _resolve_input_paths(["./downloads"])
        >>> len(result) >= 0
        True
    """
    archive_files: set[Path] = set()

    for path_str in paths:
        path = Path(path_str)

        if not path.exists():
            print(f"Warning: Path not found: {path}", file=sys.stderr)
            continue

        if path.is_file():
            if is_supported_archive(path):
                archive_files.add(path.resolve())
            else:
                print(
                    f"Warning: Unsupported file format: {path}",
                    file=sys.stderr,
                )
        elif path.is_dir():
            for item in path.iterdir():
                if item.is_file() and is_supported_archive(item):
                    archive_files.add(item.resolve())
        else:
            print(f"Warning: Unsupported path type: {path}", file=sys.stderr)

    return sorted(archive_files, key=lambda p: str(p))
```

- [ ] **Step 3: 验证函数可导入**

Run: `python -c "from try7z.main import _resolve_input_paths; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add try7z/main.py
git commit -m "feat: add _resolve_input_paths function for directory scanning"
```

---

## Task 2: 修改 `cmd_extract` 函数

**Files:**
- Modify: `try7z/main.py:653-677`

- [ ] **Step 1: 修改 `cmd_extract` 使用 `_resolve_input_paths`**

将 `cmd_extract` 函数中的：

```python
    if manager is None:
        manager = _get_password_manager()

    passwords = _build_password_list(manager, args.password)

    success_count = 0
    failure_count = 0
    total = len(args.archive)

    for archive_str in args.archive:
```

替换为：

```python
    if manager is None:
        manager = _get_password_manager()

    passwords = _build_password_list(manager, args.password)

    archive_files = _resolve_input_paths(args.archive)
    if not archive_files:
        return 0

    success_count = 0
    failure_count = 0
    total = len(archive_files)

    for archive_path in archive_files:
```

并将循环内部的：
```python
        archive_path = Path(archive_str)
```
删除（因为 `archive_path` 已经是 `Path` 对象）。

- [ ] **Step 2: 运行现有 extract 测试确保未破坏**

Run: `pytest tests/test_cli.py::TestExtractCommand -v`
Expected: 所有测试通过（约 5 个测试）

Run: `pytest tests/test_cli.py::TestExtractCommandEdgeCases -v`
Expected: 所有测试通过（约 6 个测试）

- [ ] **Step 3: Commit**

```bash
git add try7z/main.py
git commit -m "feat: integrate directory scanning into extract command"
```

---

## Task 3: 编写 `_resolve_input_paths` 单元测试

**Files:**
- Modify: `tests/test_cli.py`

- [ ] **Step 1: 在 `tests/test_cli.py` 中新增 `TestResolveInputPaths` 类**

在文件末尾（`TestMain` 类之后）添加：

```python
class TestResolveInputPaths:
    """Test cases for _resolve_input_paths function."""

    def test_single_supported_file(self, temp_dir: Path) -> None:
        """Test resolving a single supported archive file."""
        archive = temp_dir / "test.7z"
        archive.write_text("fake archive")

        result = _resolve_input_paths([str(archive)])

        assert len(result) == 1
        assert result[0] == archive.resolve()

    def test_single_directory_with_archives(self, temp_dir: Path) -> None:
        """Test resolving a directory containing multiple archives."""
        (temp_dir / "a.7z").write_text("archive a")
        (temp_dir / "b.zip").write_text("archive b")
        (temp_dir / "c.rar").write_text("archive c")
        (temp_dir / "other.txt").write_text("not an archive")

        result = _resolve_input_paths([str(temp_dir)])

        assert len(result) == 3
        names = [p.name for p in result]
        assert "a.7z" in names
        assert "b.zip" in names
        assert "c.rar" in names
        assert "other.txt" not in names

    def test_empty_directory(self, temp_dir: Path) -> None:
        """Test resolving an empty directory returns empty list."""
        result = _resolve_input_paths([str(temp_dir)])

        assert result == []

    def test_directory_with_only_unsupported_files(self, temp_dir: Path) -> None:
        """Test directory with only non-archive files returns empty list."""
        (temp_dir / "readme.txt").write_text("readme")
        (temp_dir / "data.json").write_text("{}")

        result = _resolve_input_paths([str(temp_dir)])

        assert result == []

    def test_mixed_file_and_directory(self, temp_dir: Path) -> None:
        """Test resolving a mix of file and directory paths."""
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        (subdir / "sub.7z").write_text("sub archive")

        main_archive = temp_dir / "main.zip"
        main_archive.write_text("main archive")

        result = _resolve_input_paths([str(main_archive), str(subdir)])

        assert len(result) == 2
        names = [p.name for p in result]
        assert "main.zip" in names
        assert "sub.7z" in names

    def test_unsupported_file(self, temp_dir: Path, capsys) -> None:
        """Test unsupported file prints warning and returns empty list."""
        txt_file = temp_dir / "readme.txt"
        txt_file.write_text("readme")

        result = _resolve_input_paths([str(txt_file)])

        assert result == []
        captured = capsys.readouterr()
        assert "Unsupported file format" in captured.err
        assert "readme.txt" in captured.err

    def test_nonexistent_path(self, temp_dir: Path, capsys) -> None:
        """Test nonexistent path prints warning and returns empty list."""
        missing = temp_dir / "missing.7z"

        result = _resolve_input_paths([str(missing)])

        assert result == []
        captured = capsys.readouterr()
        assert "Path not found" in captured.err
        assert "missing.7z" in captured.err

    def test_multiple_directories(self, temp_dir: Path) -> None:
        """Test resolving multiple directories."""
        dir1 = temp_dir / "dir1"
        dir1.mkdir()
        (dir1 / "a.7z").write_text("archive a")

        dir2 = temp_dir / "dir2"
        dir2.mkdir()
        (dir2 / "b.zip").write_text("archive b")

        result = _resolve_input_paths([str(dir1), str(dir2)])

        assert len(result) == 2
        names = [p.name for p in result]
        assert "a.7z" in names
        assert "b.zip" in names

    def test_duplicate_paths(self, temp_dir: Path) -> None:
        """Test duplicate paths are deduplicated."""
        archive = temp_dir / "test.7z"
        archive.write_text("archive")

        result = _resolve_input_paths([str(archive), str(archive)])

        assert len(result) == 1

    def test_case_insensitive_extensions(self, temp_dir: Path) -> None:
        """Test archive extensions are matched case-insensitively."""
        (temp_dir / "lower.7z").write_text("lower")
        (temp_dir / "upper.ZIP").write_text("upper")
        (temp_dir / "mixed.Rar").write_text("mixed")

        result = _resolve_input_paths([str(temp_dir)])

        assert len(result) == 3

    def test_result_is_sorted(self, temp_dir: Path) -> None:
        """Test result is sorted by path string."""
        (temp_dir / "z.7z").write_text("z")
        (temp_dir / "a.7z").write_text("a")
        (temp_dir / "m.7z").write_text("m")

        result = _resolve_input_paths([str(temp_dir)])

        assert len(result) == 3
        names = [p.name for p in result]
        assert names == ["a.7z", "m.7z", "z.7z"]
```

**注意**：需要在文件顶部的导入区域添加 `_resolve_input_paths` 的导入：

```python
from try7z.main import (
    # ... 现有导入 ...
    _resolve_input_paths,
    # ... 现有导入 ...
)
```

- [ ] **Step 2: 运行新增测试**

Run: `pytest tests/test_cli.py::TestResolveInputPaths -v`
Expected: 所有 11 个测试通过

- [ ] **Step 3: Commit**

```bash
git add tests/test_cli.py
git commit -m "test: add unit tests for _resolve_input_paths"
```

---

## Task 4: 编写目录解压集成测试

**Files:**
- Modify: `tests/test_cli.py`

- [ ] **Step 1: 在 `TestExtractCommandEdgeCases` 类中添加目录解压测试**

```python
    def test_extract_directory_with_archives(
        self,
        plain_7z_archive: Path,
        temp_dir: Path,
        password_manager: PasswordManager,
        capsys,
    ) -> None:
        """Test extracting from a directory containing archives."""
        args = argparse.Namespace()
        args.archive = [str(temp_dir)]
        args.output = None
        args.password = None
        args.force = True

        exit_code = cmd_extract(args, password_manager)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Success!" in captured.out
        default_output = plain_7z_archive.parent / plain_7z_archive.stem
        assert (default_output / "src" / "test.txt").exists()

    def test_extract_empty_directory(
        self, temp_dir: Path, password_manager: PasswordManager, capsys
    ) -> None:
        """Test extracting from an empty directory returns 0."""
        args = argparse.Namespace()
        args.archive = [str(temp_dir)]
        args.output = None
        args.password = None
        args.force = False

        exit_code = cmd_extract(args, password_manager)

        assert exit_code == 0

    def test_extract_directory_with_output_flag(
        self,
        plain_7z_archive: Path,
        temp_dir: Path,
        password_manager: PasswordManager,
        capsys,
    ) -> None:
        """Test extracting directory archives to specified output."""
        output_dir = temp_dir / "all_extracted"
        args = argparse.Namespace()
        args.archive = [str(temp_dir)]
        args.output = str(output_dir)
        args.password = None
        args.force = True

        exit_code = cmd_extract(args, password_manager)

        assert exit_code == 0
        assert (output_dir / "src" / "test.txt").exists()
```

- [ ] **Step 2: 运行集成测试**

Run: `pytest tests/test_cli.py::TestExtractCommandEdgeCases::test_extract_directory_with_archives -v`
Expected: PASS

Run: `pytest tests/test_cli.py::TestExtractCommandEdgeCases::test_extract_empty_directory -v`
Expected: PASS

Run: `pytest tests/test_cli.py::TestExtractCommandEdgeCases::test_extract_directory_with_output_flag -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_cli.py
git commit -m "test: add integration tests for directory extraction"
```

---

## Task 5: 验证和清理

- [ ] **Step 1: 运行完整测试套件**

Run: `pytest tests/test_cli.py -v`
Expected: 所有测试通过（原有测试 + 新增测试）

- [ ] **Step 2: 运行 lint 检查**

Run: `ruff check .`
Expected: 无错误

Run: `mypy try7z/`
Expected: 无类型错误

- [ ] **Step 3: 最终提交**

```bash
git add .
git commit -m "feat: support directory input in extract command

- Add _resolve_input_paths to scan directories for supported archives
- Integrate directory scanning into cmd_extract
- Add comprehensive unit and integration tests
- Maintain backward compatibility with existing file input"
```

---

## 自检清单

### Spec 覆盖检查

| 需求 | 实现任务 |
|------|----------|
| 目录扫描（不递归） | Task 1: `_resolve_input_paths` 使用 `path.iterdir()` |
| 格式支持（.7z/.zip/.rar） | Task 1: 使用 `is_supported_archive` 检查 |
| 输出目录行为 | Task 2: 复用现有 `_resolve_output_dir` 逻辑 |
| 空目录静默处理 | Task 2: `if not archive_files: return 0` |
| 混合输入 | Task 1: 函数同时处理文件和目录 |
| 不存在的路径警告 | Task 1: `path.exists()` 检查并打印警告 |
| 不支持的文件警告 | Task 1: `is_supported_archive` 检查并打印警告 |
| 部分失败继续处理 | Task 2: 保持现有循环逻辑 |

### 占位符检查

- [x] 无 "TBD"、"TODO"、"implement later"
- [x] 无 "Add appropriate error handling" 等模糊描述
- [x] 每个代码步骤包含完整代码
- [x] 每个测试步骤包含完整测试代码

### 类型一致性检查

- [x] `_resolve_input_paths(paths: list[str]) -> list[Path]` 类型签名一致
- [x] `archive_files: set[Path]` 与返回值 `list[Path]` 一致
- [x] `cmd_extract` 中 `archive_path` 类型保持为 `Path`

---

## 执行方式

**Plan complete and saved to `docs/superpowers/plans/2026-05-10-auto-extract-directory.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
