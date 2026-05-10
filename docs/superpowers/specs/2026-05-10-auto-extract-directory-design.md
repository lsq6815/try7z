# try7z extract 目录自动解压功能设计

## 概述

为 `try7z extract` 命令添加目录输入支持。当用户传入目录路径时，自动扫描该目录下所有支持的压缩包格式（`.7z`、`.zip`、`.rar`），并逐个解压。不递归扫描子目录。

## 背景

当前 `try7z extract` 只接受文件路径。用户解压多个压缩包时需要逐一指定，使用不便。本功能允许用户直接传入目录，工具自动发现并解压目录内所有压缩包。

## 需求

### 功能需求

1. **目录扫描**：当输入路径是目录时，扫描该目录下（不递归）所有支持的压缩包文件
2. **格式支持**：与现有支持格式一致（`.7z`、`.zip`、`.rar`，大小写不敏感）
3. **输出目录**：
   - 无 `--output`：每个压缩包解压到其所在目录下同名文件夹（保持现有行为）
   - 有 `--output`：全部解压到 `--output` 指定目录（保持现有行为）
4. **空目录处理**：目录下没有支持的压缩包时，静默返回退出码 `0`，不报错
5. **混合输入**：同时支持文件和目录的混合输入
6. **错误处理**：
   - 不存在的路径：打印警告，跳过
   - 非支持格式的文件：打印警告，跳过
   - 部分解压失败：继续处理其他文件，最终返回退出码 `1`（保持现有行为）

### 非功能需求

- 保持现有 CLI 接口不变
- 不影响单文件提取的性能和体验
- 保持代码风格与现有项目一致（PEP 604 类型注解、Google 风格 docstring）

## 架构设计

### 方案选型

**选定方案 A：路径解析函数**

在 `main.py` 中新增 `_resolve_input_paths(paths: list[str]) -> list[Path]` 函数，将混合的文件/目录输入统一解析为压缩包文件列表。`cmd_extract` 只需在开头调用此函数，其余逻辑完全不变。

选择理由：
- 职责清晰，只改 `main.py`
- 不影响 `Extractor`、`validate_archive_path` 等现有模块
- 易于测试和维护

### 接口设计

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
    """
```

## 详细设计

### 修改点

#### 1. `try7z/main.py`

**新增 `_resolve_input_paths` 函数**（放在 `_build_password_list` 附近）：

- 遍历 `paths` 列表
- 对每个路径：
  1. 检查是否存在，不存在则 `print(f"Warning: Path not found: {path}", file=sys.stderr)`，跳过
  2. 如果是文件，检查后缀是否在 `SUPPORTED_EXTENSIONS` 中，是则加入结果，否则打印警告
  3. 如果是目录，使用 `path.iterdir()` 遍历（不递归），对每个文件检查后缀，支持的加入结果
  4. 如果是其他类型（如符号链接），打印警告跳过
- 对结果去重并排序（按路径字符串排序），保证确定性输出

**修改 `cmd_extract` 函数**：

在开头增加：
```python
archive_files = _resolve_input_paths(args.archive)
if not archive_files:
    return 0
```

然后将循环 `for archive_str in args.archive:` 改为 `for archive_file in archive_files:`。

#### 2. `tests/test_main.py`

**新增测试用例**：

- `test_resolve_input_paths_single_file`：单个支持格式文件
- `test_resolve_input_paths_single_directory`：单个目录，内含多个压缩包
- `test_resolve_input_paths_empty_directory`：空目录，返回空列表
- `test_resolve_input_paths_mixed`：混合输入（文件+目录）
- `test_resolve_input_paths_unsupported_file`：不支持的格式，打印警告
- `test_resolve_input_paths_nonexistent`：不存在的路径，打印警告
- `test_cmd_extract_directory`：集成测试，验证目录输入的完整流程

### 行为矩阵

| 输入 | 场景 | 行为 |
|------|------|------|
| 单个压缩包文件 | 正常 | 正常解压（与现有行为一致） |
| 多个压缩包文件 | 正常 | 逐个解压（与现有行为一致） |
| 单个目录 | 含压缩包 | 逐个解压目录下所有支持的压缩包 |
| 单个目录 | 不含压缩包 | 静默返回 0 |
| 混合路径 | 文件+目录 | 统一解析为文件列表后处理 |
| 不存在的路径 | - | 打印警告，跳过 |
| 不支持的文件 | - | 打印警告，跳过 |

### 错误处理

- 保持现有错误处理策略不变
- `_resolve_input_paths` 中的警告信息输出到 `stderr`
- 单个压缩包解压失败不影响其他压缩包的处理
- 最终退出码逻辑保持不变（`0 if failure_count == 0 else 1`）

## 测试策略

### 单元测试

针对 `_resolve_input_paths` 函数：
1. 创建临时目录结构，放置各种测试文件
2. 验证不同输入场景下的返回值
3. 验证警告输出（使用 `capsys` 捕获 `stderr`）

### 集成测试

针对 `cmd_extract` 的目录输入场景：
1. Mock `PasswordManager` 和 `Extractor`
2. 验证目录输入时 `_resolve_input_paths` 被调用，且循环正确处理

## 兼容性

- 向后兼容：现有单文件/多文件输入行为完全不变
- CLI 参数不变：`--output`、`--password`、`--force` 等行为不变
- 不影响其他命令（`add`、`remove`、`list` 等）

## 实现计划

1. 编写 `_resolve_input_paths` 函数及单元测试
2. 修改 `cmd_extract` 函数
3. 添加集成测试
4. 运行测试和 lint 验证
