# CLI 代码重构设计文档

> **日期**: 2026-05-21
> **需求**: 将 CLI 相关代码存放到 `try7z/cli/` 下，核心代码保留在 `try7z/` 下

## 背景

当前 `try7z/` 目录下混合了 CLI 代码和核心代码：

- **CLI 代码**: `main.py`（919 行，命令处理）、`completions.py`（514 行，shell 补全）、`__main__.py`（模块入口）
- **核心代码**: `extractor.py`、`password_manager.py`、`utils.py`

随着功能增长，CLI 代码与核心代码混在一起不利于维护和清晰的责任划分。

## 目标

1. 将 CLI 相关代码（`main.py`、`completions.py`、`__main__.py`）迁移到 `try7z/cli/` 包下
2. 将 CLI 测试（`tests/test_cli.py`）迁移到 `tests/cli/` 下
3. 更新所有导入路径和项目配置
4. 不保留向后兼容的导入（用户已确认）

## 方案选择

### 方案 A：目录迁移 + 最小改动（推荐）

创建 `try7z/cli/` 包，将 CLI 文件整体移入，添加 `__init__.py` 暴露入口。同步移动测试文件。更新 `pyproject.toml` 入口点。

**优点**：
- 改动最小，风险最低
- 职责分离清晰
- 不引入额外的模块拆分复杂度

**缺点**：
- `main.py` 仍然较大（900+ 行），但这是现有问题，不在本次重构范围内

### 方案 B：模块进一步拆分

在方案 A 基础上，将 `main.py` 拆分为 `parser.py`、`commands.py`、`strategies.py`。

**优点**：更细粒度的职责分离
**缺点**：改动过大，调整测试导入的工作量大，引入不必要的风险

### 方案 C：软链接/兼容层

保持文件不动，通过重新导出制造"逻辑分离"。

**优点**：零文件移动风险
**缺点**：不满足真实目录分离需求，结构混乱

**最终选择：方案 A**

## 目录结构

### 变更前

```
try7z/
├── __init__.py
├── __main__.py
├── main.py              # CLI 命令处理
├── completions.py       # Shell 补全
├── extractor.py         # 核心：解压逻辑
├── password_manager.py  # 核心：密码管理
├── utils.py             # 核心：工具函数
└── lib/

tests/
├── test_cli.py
├── test_extractor.py
├── test_password_manager.py
├── test_utils.py
├── conftest.py
└── benchmark_*.py
```

### 变更后

```
try7z/
├── __init__.py
├── extractor.py         # 核心：解压逻辑
├── password_manager.py  # 核心：密码管理
├── utils.py             # 核心：工具函数
├── cli/                 # NEW: CLI 包
│   ├── __init__.py      # 暴露 main 入口
│   ├── __main__.py      # python -m try7z.cli
│   ├── main.py          # 命令处理（从 try7z/ 移入）
│   └── completions.py   # shell 补全（从 try7z/ 移入）
└── lib/

tests/
├── test_extractor.py
├── test_password_manager.py
├── test_utils.py
├── conftest.py
├── benchmark_*.py
└── cli/                 # NEW: CLI 测试
    └── test_cli.py      # 从 tests/ 移入
```

## 关键变更点

### 1. 入口点配置（pyproject.toml）

```toml
[project.scripts]
try7z = "try7z.cli:main"
```

### 2. try7z/cli/__init__.py（新增）

```python
"""CLI package for try7z."""

from try7z.cli.main import main

__all__ = ["main"]
```

### 3. try7z/cli/__main__.py（从 try7z/__main__.py 移入并修改）

```python
"""Entry point for running try7z CLI as a module."""

import sys

from try7z.cli import main

if __name__ == "__main__":
    sys.exit(main())
```

### 4. try7z/cli/main.py（从 try7z/main.py 移入）

文件内容基本不变，仅需修改 `try7z.completions` 导入为 `try7z.cli.completions`：

```python
# 修改前
from try7z.completions import (
    generate_bash_completion,
    generate_powershell_completion,
    generate_pwsh_completion,
    install_completion,
)

# 修改后
from try7z.cli.completions import (
    generate_bash_completion,
    generate_powershell_completion,
    generate_pwsh_completion,
    install_completion,
)
```

其他核心模块导入路径保持不变（如 `from try7z.extractor import ...`），因为它们仍在 `try7z/` 下。

### 5. 测试文件导入（tests/cli/test_cli.py）

```python
# 修改前
from try7z.main import (
    cmd_add_password,
    cmd_autocompletion,
    ...
)

# 修改后
from try7z.cli.main import (
    cmd_add_password,
    cmd_autocompletion,
    ...
)
```

## 注意事项

1. **myproject.toml 的 include 规则**：`try7z*` 已经包含 `try7z/cli/`，无需修改
2. **mypy 配置**：`files = ["try7z", "docs", "tests"]` 已经包含子目录，无需修改
3. **pytest 配置**：`testpaths = ["tests"]` 会自动发现 `tests/cli/`，无需修改
4. **coverage 配置**：`source = ["try7z"]` 已经包含子目录，无需修改
5. **ruff**：会自动处理所有 Python 文件，无需额外配置

## 测试验证

重构完成后需运行：

```bash
pytest                    # 确保所有测试通过
ruff check .             # 确保代码风格正确
mypy try7z/              # 确保类型检查通过
python -m try7z --help   # 确保 CLI 入口正常
```
