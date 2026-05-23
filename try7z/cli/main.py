"""CLI entry point and command handlers for try7z.

This module provides the command-line interface for managing passwords
and extracting archives. It uses argparse for command parsing and
dispatches to appropriate handler functions.

Commands:
    add: Add one or more passwords to the stored list
    remove: Remove passwords by value or index
    list: Display all stored passwords with indices
    clear: Remove all stored passwords
    path: Show the location of the passwords file
    edit: Open the passwords file in the default editor
    extract: Extract an archive using stored passwords
    autocompletion: Generate shell completion script

Usage:
    Basic command structure::

        $ try7z <command> [options]

    Examples::

        $ try7z add "mypassword"
        $ try7z add "pwd1" "pwd2" "pwd3"
        $ try7z list
        $ try7z remove -i 2 3
        $ try7z extract archive.7z -o output_dir

    See individual command help::

        $ try7z <command> --help

Exit Codes:
    0: Success
    1: Error (invalid arguments, operation failed, etc.)

Example:
    Using argparse.Namespace for testing::

        >>> import argparse
        >>> from try7z.cli.main import cmd_list_passwords
        >>>
        >>> args = argparse.Namespace()
        >>> exit_code = cmd_list_passwords(args)
"""

import argparse
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from try7z import __build_date__, __version__
from try7z.cli.completions import (
    generate_bash_completion,
    generate_powershell_completion,
    generate_pwsh_completion,
    install_completion,
)
from try7z.extractor import Extractor, get_7z_version
from try7z.password_manager import PasswordManager
from try7z.utils import (
    PasswordNotFoundError,
    PasswordValidationError,
    Try7zError,
    is_supported_archive,
)


@dataclass
class RemovalResult:
    """Result of a password removal operation.

    Attributes:
        removed_count: Number of passwords successfully removed.
        failures: List of failure messages for items that could not be removed.
        success_messages: List of success messages for removed items.
    """

    removed_count: int
    failures: list[str]
    success_messages: list[str]


class RemovalStrategy(Protocol):
    """Protocol for password removal strategies."""

    def execute(self, manager: PasswordManager) -> RemovalResult:
        """Execute the removal strategy.

        Args:
            manager: PasswordManager instance to operate on.

        Returns:
            RemovalResult containing operation outcome.
        """
        ...


def _get_password_manager() -> PasswordManager:
    """Factory function for creating PasswordManager instances.

    Centralizes PasswordManager instantiation so that the storage backend
    can be swapped without modifying every command handler.

    Returns:
        A new PasswordManager instance using the default configuration.
    """
    return PasswordManager()


class RemoveByValueStrategy:
    """Remove passwords by their string value.

    Deduplicates the password list while preserving order, then attempts
    to remove each password from the manager.
    """

    def __init__(self, passwords: list[str]) -> None:
        """Initialize with list of passwords to remove.

        Args:
            passwords: List of password strings to remove.
        """
        self.passwords = list(dict.fromkeys(passwords))

    def execute(self, manager: PasswordManager) -> RemovalResult:
        """Execute removal by value.

        Args:
            manager: PasswordManager instance to remove passwords from.

        Returns:
            RemovalResult with operation outcome.
        """
        result = RemovalResult(0, [], [])
        for pwd in self.passwords:
            try:
                manager.remove_password(pwd)
                result.success_messages.append(f"Removed: {pwd}")
                result.removed_count += 1
            except Try7zError:  # noqa: PERF203
                result.failures.append(f"Password '{pwd}' not found")
        return result


class RemoveByIndexStrategy:
    """Remove passwords by their 1-based index.

    Deduplicates indices, converts to 0-based, sorts in descending order
    to avoid index shifting during removal.
    """

    def __init__(self, indices: list[int]) -> None:
        """Initialize with list of 1-based indices to remove.

        Args:
            indices: List of 1-based indices to remove.
        """
        unique = list(dict.fromkeys(indices))
        self.indices = sorted([i - 1 for i in unique], reverse=True)

    def execute(self, manager: PasswordManager) -> RemovalResult:
        """Execute removal by index.

        Args:
            manager: PasswordManager instance to remove passwords from.

        Returns:
            RemovalResult with operation outcome.
        """
        result = RemovalResult(0, [], [])
        for idx in self.indices:
            try:
                removed = manager.remove_by_index(idx)
                result.success_messages.append(f"Removed [{idx + 1}]: {removed}")
                result.removed_count += 1
            except Try7zError:  # noqa: PERF203
                result.failures.append(f"Index {idx + 1} out of range")
        return result


def _report_removal_result(result: RemovalResult, total_count: int) -> None:
    """Report removal operation results.

    Prints success messages, failure warnings, and summary count.

    Args:
        result: RemovalResult from strategy execution.
        total_count: Total passwords remaining after operation.
    """
    for msg in result.success_messages:
        print(f"  {msg}")
    for failure in result.failures:
        print(f"Warning: {failure}", file=sys.stderr)
    print(f"Removed {result.removed_count} password(s). Total: {total_count}")


def cmd_add_password(
    args: argparse.Namespace,
    manager: PasswordManager | None = None,
) -> int:
    """Add password(s) to the stored list.

    Adds one or more passwords to the password manager. Duplicate
    passwords are skipped with a warning. Invalid passwords (empty,
    whitespace-only, too long) are also skipped with warnings.
    Reports the number of passwords added and skipped.

    Args:
        args: Parsed command line arguments. Expected attributes:
            - passwords: List of password strings to add
        manager: Optional PasswordManager instance for testing.
                If None, creates a new instance.

    Returns:
        Exit code (0 if at least one password was added, 1 otherwise).

    Example:
        >>> import argparse
        >>> args = argparse.Namespace()
        >>> args.passwords = ["secret123", "another_pwd"]
        >>> cmd_add_password(args)  # Adds both passwords
        0
    """
    if manager is None:
        manager = _get_password_manager()

    added_count = 0
    skipped_count = 0
    added_passwords: list[str] = []

    for password in args.passwords:
        try:
            manager.add_password(password)
            added_count += 1
            added_passwords.append(password)
        except PasswordValidationError as e:  # noqa: PERF203
            print(f"Warning: {e}, skipped", file=sys.stderr)
            skipped_count += 1
        except Try7zError:
            print(f"Warning: Password '{password}' already exists", file=sys.stderr)
            skipped_count += 1

    if added_count > 0:
        display_passwords = added_passwords[:5]
        password_list = ", ".join(f"'{p}'" for p in display_passwords)
        if len(added_passwords) > 5:
            password_list += f", and {len(added_passwords) - 5} more"
        print(f"Added {added_count} password(s): {password_list}. Total: {manager.count()}")
    if skipped_count > 0:
        print(f"Skipped {skipped_count} invalid/duplicate password(s)")

    return 0


def cmd_remove_password(
    args: argparse.Namespace,
    manager: PasswordManager | None = None,
) -> int:
    """Remove password(s) by value or index.

    Removes passwords either by their string value or by their
    1-based index (as shown by the 'list' command). Cannot use
    both methods simultaneously.

    Args:
        args: Parsed command line arguments. Expected attributes:
            - password: List of password strings to remove (optional)
            - index: List of 1-based indices to remove (optional)
        manager: Optional PasswordManager instance for testing.
                If None, creates a new instance.

    Returns:
        Exit code (0 on success, 1 on error).

    Raises:
        Prints error to stderr if both password and index are provided,
        or if neither is provided.

    Example:
        Remove by value::

            >>> args = argparse.Namespace()
            >>> args.password = ["old_password"]
            >>> args.index = None
            >>> cmd_remove_password(args)
            0

        Remove by index::

            >>> args.password = []
            >>> args.index = [1, 3]  # Removes 1st and 3rd passwords
            >>> cmd_remove_password(args)
            0
    """
    if manager is None:
        manager = _get_password_manager()

    # Validate: cannot use both methods
    if args.password and args.index:
        print("Error: Cannot use both password value and --index", file=sys.stderr)
        return 1

    # Validate: must use at least one method
    if not args.password and not args.index:
        print("Error: Please specify password(s) or use --index", file=sys.stderr)
        return 1

    strategy: RemovalStrategy
    if args.index:
        strategy = RemoveByIndexStrategy(args.index)
    else:
        strategy = RemoveByValueStrategy(args.password)

    result = strategy.execute(manager)
    _report_removal_result(result, manager.count())
    return 0


def cmd_list_passwords(
    args: argparse.Namespace,
    manager: PasswordManager | None = None,
) -> int:
    """List all stored passwords with 1-based indices.

    Displays all stored passwords with their indices. The indices
    can be used with the 'remove -i' command.

    Args:
        args: Parsed command line arguments (no specific attributes used).
        manager: Optional PasswordManager instance for testing.
                If None, creates a new instance.

    Returns:
        Exit code (always 0).

    Example:
        >>> args = argparse.Namespace()
        >>> cmd_list_passwords(args)
        Stored passwords (3):
          1. password_one
          2. password_two
          3. password_three
        0
    """
    if manager is None:
        manager = _get_password_manager()
    passwords = manager.get_passwords()

    if not passwords:
        print("No passwords stored.")
        return 0

    print(f"Stored passwords ({manager.count()}):")
    max_display_len = max(40, shutil.get_terminal_size().columns - 10)
    for i, pw in enumerate(passwords, 1):
        display_pw = pw if len(pw) <= max_display_len else pw[: max_display_len - 3] + "..."
        print(f"  {i}. {display_pw}")

    return 0


def cmd_clear_passwords(
    args: argparse.Namespace,
    manager: PasswordManager | None = None,
) -> int:
    """Clear all stored passwords.

    Removes all passwords from storage. By default, prompts for
    confirmation unless the -f/--force flag is used.

    Args:
        args: Parsed command line arguments. Expected attributes:
            - force: Boolean indicating whether to skip confirmation
        manager: Optional PasswordManager instance for testing.
                If None, creates a new instance.

    Returns:
        Exit code (always 0).

    Example:
        With confirmation (user must type 'y')::

            >>> args = argparse.Namespace()
            >>> args.force = False
            >>> cmd_clear_passwords(args)
            Clear all passwords? [y/N]:

        Without confirmation::

            >>> args.force = True
            >>> cmd_clear_passwords(args)
            All passwords cleared.
            0
    """
    if not args.force:
        confirm = input("Clear all passwords? [y/N]: ")
        if confirm.lower() != "y":
            print("Cancelled.")
            return 0

    if manager is None:
        manager = _get_password_manager()
    manager.clear_passwords()
    print("All passwords cleared.")
    return 0


def cmd_show_path(
    args: argparse.Namespace,
    manager: PasswordManager | None = None,
) -> int:
    """Show the passwords file path.

    Displays the full path to the passwords.json file where
    passwords are stored.

    Args:
        args: Parsed command line arguments (no specific attributes used).
        manager: Optional PasswordManager instance for testing.
                If None, creates a new instance.

    Returns:
        Exit code (always 0).

    Example:
        >>> args = argparse.Namespace()
        >>> cmd_show_path(args)
        C:\\Users\\Username\\AppData\\Roaming\\try7z\\passwords.json
        0
    """
    if manager is None:
        manager = _get_password_manager()
    print(manager.passwords_file)
    return 0


def cmd_edit_passwords(
    args: argparse.Namespace,
    manager: PasswordManager | None = None,
) -> int:
    """Open passwords file in the default system editor.

    Opens the passwords.json file using the system's default
    application for JSON files. Creates the file if it doesn't exist.

    Args:
        args: Parsed command line arguments (no specific attributes used).
        manager: Optional PasswordManager instance for testing.
                If None, creates a new instance.

    Returns:
        Exit code (0 on success, 1 on error).

    Note:
        Uses platform-specific methods:
        - Windows: os.startfile()
        - macOS: open command
        - Linux: xdg-open command

    Example:
        >>> args = argparse.Namespace()
        >>> cmd_edit_passwords(args)
        0
    """
    if manager is None:
        manager = _get_password_manager()
    passwords_file = str(manager.passwords_file)

    # Ensure file exists
    manager.passwords_file.touch(exist_ok=True)

    system = os.name
    try:
        if system == "nt":  # Windows
            os.startfile(passwords_file)
        elif sys.platform == "darwin":  # macOS
            subprocess.run(["open", passwords_file], check=True)
        else:  # Linux
            subprocess.run(["xdg-open", passwords_file], check=True)
        return 0
    except Exception as e:
        print(f"Error opening file: {e}", file=sys.stderr)
        return 1


def _build_password_list(
    manager: PasswordManager, priority_password: str | None = None
) -> list[str]:
    """Build the password list from stored passwords and optional priority password.

    Args:
        manager: PasswordManager instance to retrieve stored passwords from.
        priority_password: Optional password to try first before stored passwords.

    Returns:
        List of passwords to try, with priority password first if provided.
    """
    passwords = manager.get_passwords()
    if priority_password:
        passwords = [priority_password, *passwords]
    return passwords


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
        >>> from try7z.cli.main import _resolve_input_paths
        >>> # Resolve a single archive file
        >>> result = _resolve_input_paths(["archive.7z"])  # File must exist
        >>> len(result) == 1 if result else True
        True
        >>> # Resolve a directory containing archives
        >>> result = _resolve_input_paths(["./downloads"])  # Dir must exist
        >>> isinstance(result, list)
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


def _resolve_output_dir(
    archive_path: Path,
    output_base: str | None = None,
    use_subdirectory: bool = False,
) -> Path:
    """Resolve the output directory for an archive extraction.

    Args:
        archive_path: Path to the archive file.
        output_base: Optional base output directory path.
        use_subdirectory: Whether to create a subdirectory named after the archive
                         when output_base is provided (used for multi-archive extraction).

    Returns:
        Resolved absolute path for the output directory.
    """
    if output_base:
        output_dir = Path(output_base)
        if use_subdirectory:
            output_dir = output_dir / archive_path.stem
    else:
        output_dir = archive_path.parent / archive_path.stem
    return output_dir.resolve()


def _handle_existing_output(output_dir: Path, force: bool) -> bool:
    """Handle existing output directory/file during extraction.

    Args:
        output_dir: Path to the output directory or file.
        force: Whether to overwrite without confirmation.

    Returns:
        True if extraction should proceed, False if cancelled by user.
    """
    if not output_dir.exists():
        return True

    item_type = "directory" if output_dir.is_dir() else "file"
    if force:
        print(
            f"Warning: Output {item_type} '{output_dir.name}' already exists "
            "and will be overwritten."
        )
        return True

    confirm = input(
        f"Output {item_type} '{output_dir.name}' already exists. Overwrite? [y/N]: "
    )
    if confirm.lower() != "y":
        print("Extraction cancelled.")
        return False

    # Remove existing directory/file
    if output_dir.is_dir():
        shutil.rmtree(output_dir)
    else:
        output_dir.unlink()
    return True


def _extract_single(
    archive_path: Path,
    output_dir: Path,
    passwords: list[str],
    force: bool,
    flatten: bool = False,
) -> int:
    """Extract a single archive and return exit code."""
    try:
        extractor = Extractor(archive_path)
    except Try7zError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if not _handle_existing_output(output_dir, force):
        return 1

    print(f"Attempting to extract: {archive_path.name}")
    print(f"Trying {len(passwords)} password(s)...")

    try:
        success, used_password = extractor.extract_with_passwords(
            passwords, output_dir, show_progress=True, show_password_progress=True,
            flatten=flatten,
        )

        if success:
            if used_password:
                print("Success! Extracted with password.")
            else:
                print("Success! Archive was not password-protected.")

            print(f"Extracted to: {output_dir}")
            return 0
        print("Extraction failed.", file=sys.stderr)
        return 1

    except PasswordNotFoundError:
        print("No matching password found", file=sys.stderr)
        return 1
    except Try7zError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_extract(
    args: argparse.Namespace,
    manager: PasswordManager | None = None,
) -> int:
    """Extract archive(s) using stored passwords.

    Extracts password-protected archive(s) by trying all stored
    passwords (plus an optional additional password). Reports
    success or failure to the user.

    Args:
        args: Parsed command line arguments. Expected attributes:
            - archive: List of paths to archive files
            - output: Optional output directory path
            - password: Optional additional password to try first
            - force: Boolean indicating whether to skip overwrite confirmation
        manager: Optional PasswordManager instance for testing.
                If None, creates a new instance.

    Returns:
        Exit code (0 on success, 1 on error).

    Example:
        Basic extraction::

            >>> args = argparse.Namespace()
            >>> args.archive = ["secret.7z"]
            >>> args.output = None
            >>> args.password = None
            >>> args.force = False
            >>> cmd_extract(args)
            Attempting to extract: secret.7z
            Trying 5 password(s)...
            Success! Extracted with password.
            0

        With custom output and priority password::

            >>> args.output = "./extracted"
            >>> args.password = "try_this_first"
            >>> cmd_extract(args)
    """
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
        output_dir = _resolve_output_dir(
            archive_path, args.output, use_subdirectory=(total > 1)
        )

        result = _extract_single(archive_path, output_dir, passwords, args.force, flatten=args.flatten)
        if result == 0:
            success_count += 1
        else:
            failure_count += 1

    if total > 1:
        print(f"\nSummary: {success_count} succeeded, {failure_count} failed")

    return 0 if failure_count == 0 else 1


def cmd_autocompletion(args: argparse.Namespace) -> int:
    """Generate or install shell completion script.

    Generates completion scripts for bash or PowerShell. When --install
    is used, installs the script to the shell's configuration directory.

    Args:
        args: Parsed command line arguments. Expected attributes:
            - shell: Target shell ("bash", "pwsh", or "powershell")
            - install: Whether to install instead of printing to stdout

    Returns:
        Exit code (0 on success, 1 on error).

    Example:
        Print bash completion script::

            >>> args = argparse.Namespace()
            >>> args.shell = "bash"
            >>> args.install = False
            >>> cmd_autocompletion(args)
            0

        Install PowerShell completion::

            >>> args.shell = "pwsh"
            >>> args.install = True
            >>> cmd_autocompletion(args)
            0
    """
    shell: str = args.shell

    if shell == "bash":
        script = generate_bash_completion()
    elif shell == "pwsh":
        script = generate_pwsh_completion()
    elif shell == "powershell":
        script = generate_powershell_completion()
    else:
        print(
            f"Error: Unsupported shell '{shell}'. "
            "Use 'bash', 'pwsh', or 'powershell'.",
            file=sys.stderr,
        )
        return 1

    if args.install:
        try:
            install_completion(shell)
            print(f"Completion script installed for {shell}.")
            if shell == "bash":
                print("Run 'source ~/.bashrc' or restart your terminal to activate.")
            elif shell == "pwsh":
                print("Restart PowerShell or run '. $PROFILE' to activate.")
        except (OSError, ValueError) as e:
            print(f"Error installing completion: {e}", file=sys.stderr)
            return 1
    else:
        print(script, end="")

    return 0


def main() -> int:
    """Main entry point for the CLI application.

    Parses command-line arguments and dispatches to the appropriate
    handler function. Supports --version and --help flags.

    Returns:
        Exit code from the executed command.

    Example:
        Command-line usage::

            $ try7z --version
            $ try7z --help
            $ try7z add "password"
            $ try7z extract archive.7z
    """
    parser = argparse.ArgumentParser(
        prog="try7z",
        description="Auto-extract password-protected archives",
        add_help=False,
    )
    parser.add_argument(
        "-h",
        "--help",
        action="help",
        default=argparse.SUPPRESS,
        help="Show this help message and exit",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="store_true",
        help="Show version information and exit",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    add_parser = subparsers.add_parser("add", help="Add password(s)")
    add_parser.add_argument("passwords", nargs="+", help="Password(s) to add")
    add_parser.set_defaults(func=cmd_add_password)

    remove_parser = subparsers.add_parser("remove", help="Remove password(s) by value or index")
    remove_parser.add_argument("password", nargs="*", help="Password(s) to remove")
    remove_parser.add_argument(
        "-i",
        "--index",
        nargs="+",
        type=int,
        metavar="N",
        help="Index(es) to remove (1-based, from 'list' command)",
    )
    remove_parser.set_defaults(func=cmd_remove_password)

    list_parser = subparsers.add_parser("list", help="List stored passwords")
    list_parser.set_defaults(func=cmd_list_passwords)

    clear_parser = subparsers.add_parser("clear", help="Clear all passwords")
    clear_parser.add_argument("-f", "--force", action="store_true", help="Skip confirmation")
    clear_parser.set_defaults(func=cmd_clear_passwords)

    path_parser = subparsers.add_parser("path", help="Show passwords file path")
    path_parser.set_defaults(func=cmd_show_path)

    edit_parser = subparsers.add_parser("edit", help="Open passwords file in default editor")
    edit_parser.set_defaults(func=cmd_edit_passwords)

    extract_parser = subparsers.add_parser("extract", help="Extract archive(s)")
    extract_parser.add_argument("archive", nargs="+", help="Path to archive file(s)")
    extract_parser.add_argument("-o", "--output", help="Output directory")
    extract_parser.add_argument("-p", "--password", help="Additional password to try first")
    extract_parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Overwrite output directory without confirmation",
    )
    extract_parser.add_argument(
        "-F",
        "--flatten",
        action="store_true",
        help="Flatten single-child intermediate directories in extracted output",
    )
    extract_parser.set_defaults(func=cmd_extract)

    completion_parser = subparsers.add_parser(
        "autocompletion", help="Generate shell completion script"
    )
    completion_parser.add_argument(
        "--shell",
        choices=["bash", "pwsh", "powershell"],
        required=True,
        help="Target shell for completion script",
    )
    completion_parser.add_argument(
        "--install",
        action="store_true",
        help="Install completion script to shell configuration",
    )
    completion_parser.set_defaults(func=cmd_autocompletion)

    args = parser.parse_args()

    if args.version:
        print(f"try7z {__version__}")
        print(f"Built: {__build_date__}")
        print()
        print("A 7-Zip frontend for auto-extracting password-protected archives")
        print()
        print(f"Using 7-Zip binary: {get_7z_version()}")
        return 0

    if args.command is None:
        parser.print_help()
        return 0

    func: Callable[[argparse.Namespace], int] = args.func
    return func(args)


if __name__ == "__main__":
    sys.exit(main())
