# CLI 代码重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 CLI 相关代码迁移到 `try7z/cli/` 和 `tests/cli/` 目录下，核心代码保留在 `try7z/` 根目录。

**Architecture:** 创建独立的 `try7z.cli` 包存放 CLI 入口、命令处理和 shell 补全逻辑；`try7z/` 根目录仅保留 `extractor`、`password_manager`、`utils` 三个核心模块；同步在 `tests/cli/` 下管理 CLI 测试。

**Tech Stack:** Python 3.10+, pytest, ruff, mypy

---

## 文件结构映射

### 创建文件
- `try7z/cli/__init__.py` — 暴露 `main` 入口函数
- `try7z/cli/__main__.py` — `python -m try7z.cli` 模块入口

### 移动并修改文件
- `try7z/main.py` → `try7z/cli/main.py` — 修改内部 `completions` 导入路径
- `try7z/completions.py` → `try7z/cli/completions.py` — 无需代码改动
- `try7z/__main__.py` → `try7z/cli/__main__.py` — 修改 `main` 导入路径
- `tests/test_cli.py` → `tests/cli/test_cli.py` — 修改所有 CLI 导入路径

### 修改文件
- `pyproject.toml` — 更新 CLI 入口点

### 删除文件
- `try7z/main.py`（移动后删除）
- `try7z/completions.py`（移动后删除）
- `try7z/__main__.py`（移动后删除）
- `tests/test_cli.py`（移动后删除）

---

## Task 1: 创建 try7z/cli/ 包目录结构

**Files:**
- Create: `try7z/cli/__init__.py`
- Create: `try7z/cli/__main__.py`

- [ ] **Step 1: 创建目录**

```bash
mkdir try7z/cli
```

- [ ] **Step 2: 创建 `try7z/cli/__init__.py`**

```python
"""CLI package for try7z.

This package provides the command-line interface for managing passwords
and extracting archives.

Example:
    Import the CLI entry point::

        >>> from try7z.cli import main
        >>> # main()  # Would start the CLI

    Run as a module::

        $ python -m try7z.cli
"""

from try7z.cli.main import main

__all__ = ["main"]
```

- [ ] **Step 3: 创建 `try7z/cli/__main__.py`**

```python
"""Entry point for running try7z CLI as a module.

This module allows the CLI to be executed using Python's -m flag::

    python -m try7z.cli [command] [options]

This is equivalent to running the ``try7z`` CLI command after
installation. All commands and options are identical.

Example:
    Show help::

        $ python -m try7z.cli --help

    Add a password::

        $ python -m try7z.cli add "mypassword"

    Extract an archive::

        $ python -m try7z.cli extract archive.7z

Note:
    This module calls :func:`try7z.cli.main`.
    See :mod:`try7z.cli.main` for the full CLI documentation.
"""

import sys

from try7z.cli import main

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: 验证目录创建成功**

```bash
ls try7z/cli/
```

Expected output: `__init__.py  __main__.py`

- [ ] **Step 5: Commit**

```bash
git add try7z/cli/
git commit -m "chore: create try7z/cli package structure"
```

---

## Task 2: 移动并修改 completions.py

**Files:**
- Move: `try7z/completions.py` → `try7z/cli/completions.py`
- Delete: `try7z/completions.py`

- [ ] **Step 1: 复制文件到新位置**

```bash
cp try7z/completions.py try7z/cli/completions.py
```

- [ ] **Step 2: 验证文件内容无需修改**

`try7z/cli/completions.py` 中的导入都是标准库（`subprocess`, `sys`, `pathlib`），不涉及 `try7z` 内部模块，因此无需修改代码。

- [ ] **Step 3: 删除旧文件**

```bash
git rm try7z/completions.py
```

- [ ] **Step 4: Commit**

```bash
git add try7z/cli/completions.py
git commit -m "refactor: move completions.py to try7z/cli/"
```

---

## Task 3: 移动并修改 main.py

**Files:**
- Move: `try7z/main.py` → `try7z/cli/main.py`
- Modify: `try7z/cli/main.py` — 更新 completions 导入路径
- Delete: `try7z/main.py`

- [ ] **Step 1: 复制文件到新位置**

```bash
cp try7z/main.py try7z/cli/main.py
```

- [ ] **Step 2: 修改导入路径**

在 `try7z/cli/main.py` 中，将 `try7z.completions` 的导入改为 `try7z.cli.completions`：

找到这段代码（约第 59-64 行）：

```python
from try7z.completions import (
    generate_bash_completion,
    generate_powershell_completion,
    generate_pwsh_completion,
    install_completion,
)
```

替换为：

```python
from try7z.cli.completions import (
    generate_bash_completion,
    generate_powershell_completion,
    generate_pwsh_completion,
    install_completion,
)
```

- [ ] **Step 3: 删除旧文件**

```bash
git rm try7z/main.py
```

- [ ] **Step 4: Commit**

```bash
git add try7z/cli/main.py
git commit -m "refactor: move main.py to try7z/cli/ and update imports"
```

---

## Task 4: 更新 pyproject.toml 入口点

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: 修改入口点**

找到 `[project.scripts]` 部分：

```toml
[project.scripts]
try7z = "try7z.main:main"
```

替换为：

```toml
[project.scripts]
try7z = "try7z.cli:main"
```

- [ ] **Step 2: Commit**

```bash
git add pyproject.toml
git commit -m "refactor: update CLI entry point to try7z.cli:main"
```

---

## Task 5: 移动并修改测试文件

**Files:**
- Create: `tests/cli/__init__.py`
- Move: `tests/test_cli.py` → `tests/cli/test_cli.py`
- Modify: `tests/cli/test_cli.py` — 更新所有导入路径
- Delete: `tests/test_cli.py`

- [ ] **Step 1: 创建测试目录和 __init__.py**

```bash
mkdir tests/cli
touch tests/cli/__init__.py
```

- [ ] **Step 2: 复制测试文件**

```bash
cp tests/test_cli.py tests/cli/test_cli.py
```

- [ ] **Step 3: 修改导入路径**

在 `tests/cli/test_cli.py` 中，将所有 `from try7z.main import ...` 改为 `from try7z.cli.main import ...`。

找到以下导入（约第 11-27 行）：

```python
from try7z.extractor import get_7z_version
from try7z.main import (
    RemovalResult,
    RemoveByIndexStrategy,
    RemoveByValueStrategy,
    _report_removal_result,
    _resolve_input_paths,
    cmd_add_password,
    cmd_autocompletion,
    cmd_clear_passwords,
    cmd_edit_passwords,
    cmd_extract,
    cmd_list_passwords,
    cmd_remove_password,
    cmd_show_path,
    main,
)
```

替换为：

```python
from try7z.extractor import get_7z_version
from try7z.cli.main import (
    RemovalResult,
    RemoveByIndexStrategy,
    RemoveByValueStrategy,
    _report_removal_result,
    _resolve_input_paths,
    cmd_add_password,
    cmd_autocompletion,
    cmd_clear_passwords,
    cmd_edit_passwords,
    cmd_extract,
    cmd_list_passwords,
    cmd_remove_password,
    cmd_show_path,
    main,
)
```

- [ ] **Step 4: 检查文件中是否还有其他从 try7z.main 的导入**

搜索 `try7z.main`：

```bash
grep -n "try7z\.main" tests/cli/test_cli.py
```

Expected: 无匹配（或只有已修改的那一处）。如果有其他引用，一并修改。

- [ ] **Step 5: 删除旧测试文件**

```bash
git rm tests/test_cli.py
```

- [ ] **Step 6: Commit**

```bash
git add tests/cli/
git commit -m "refactor: move test_cli.py to tests/cli/ and update imports"
```

---

## Task 6: 验证重构结果

**Files:**
- 所有已变更的文件

- [ ] **Step 1: 运行单元测试**

```bash
pytest -m "not benchmark"
```

Expected: 所有测试通过

- [ ] **Step 2: 运行代码风格检查**

```bash
ruff check .
```

Expected: 无错误

- [ ] **Step 3: 运行类型检查**

```bash
mypy try7z/
```

Expected: 无类型错误

- [ ] **Step 4: 验证 CLI 入口可用**

```bash
python -m try7z.cli --help
```

Expected: 显示 help 信息，无 ImportError

- [ ] **Step 5: 检查旧文件是否已清理**

```bash
ls try7z/main.py try7z/completions.py try7z/__main__.py tests/test_cli.py
```

Expected: 所有文件不存在（No such file or directory）

- [ ] **Step 6: 最终 Commit**

```bash
git add -A
git commit -m "refactor: reorganize CLI code into try7z/cli package"
```

---

## Self-Review

### Spec Coverage
- ✅ 创建 `try7z/cli/` 包（Task 1）
- ✅ 移动 `main.py` 到 `try7z/cli/main.py`（Task 3）
- ✅ 移动 `completions.py` 到 `try7z/cli/completions.py`（Task 2）
- ✅ 移动 `__main__.py` 到 `try7z/cli/__main__.py`（Task 1）
- ✅ 更新 `pyproject.toml` 入口点（Task 4）
- ✅ 移动 `tests/test_cli.py` 到 `tests/cli/test_cli.py`（Task 5）
- ✅ 验证步骤（Task 6）

### Placeholder Scan
- ✅ 无 "TBD"、"TODO" 等占位符
- ✅ 所有步骤包含具体代码和命令
- ✅ 无模糊的描述

### Type Consistency
- ✅ `try7z.cli:main` 入口点与 `try7z.cli.__init__.py` 中的导出一致
- ✅ 所有导入路径在移动后保持一致

---

## 执行选项

**Plan complete and saved to `docs/superpowers/plans/2026-05-21-cli-refactoring.md`.**

**Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
