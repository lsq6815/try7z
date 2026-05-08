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
        >>> from try7z.main import cmd_list_passwords
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
from pathlib import Path

from try7z import __build_date__, __version__
from try7z.completions import (
    generate_bash_completion,
    generate_powershell_completion,
    generate_pwsh_completion,
    install_completion,
)
from try7z.extractor import Extractor, get_7z_version
from try7z.password_manager import PasswordManager
from try7z.utils import PasswordNotFoundError, Try7zError


def cmd_add_password(
    args: argparse.Namespace,
    manager: PasswordManager | None = None,
) -> int:
    """Add password(s) to the stored list.

    Adds one or more passwords to the password manager. Duplicate
    passwords are skipped with a warning. Reports the number of
    passwords added and skipped.

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
        manager = PasswordManager()

    added_count = 0
    skipped_count = 0
    added_passwords: list[str] = []

    for password in args.passwords:
        try:
            manager.add_password(password)
            added_count += 1
            added_passwords.append(password)
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
        print(f"Skipped {skipped_count} duplicate(s)")

    return 0 if added_count > 0 else 1


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
        manager = PasswordManager()

    # Validate: cannot use both methods
    if args.password and args.index:
        print("Error: Cannot use both password value and --index", file=sys.stderr)
        return 1

    # Validate: must use at least one method
    if not args.password and not args.index:
        print("Error: Please specify password(s) or use --index", file=sys.stderr)
        return 1

    try:
        if args.index:
            # Remove by index
            # Deduplicate while preserving order
            seen = set()
            unique_indices = []
            for idx in args.index:
                if idx not in seen:
                    seen.add(idx)
                    unique_indices.append(idx)

            # Convert to 0-based and sort (descending to avoid index shifting)
            indices_0based = sorted([i - 1 for i in unique_indices], reverse=True)

            removed_count = 0
            failed_indices = []

            for idx in indices_0based:
                try:
                    removed_pw = manager.remove_by_index(idx)
                    print(f"  Removed [{idx + 1}]: {removed_pw}")
                    removed_count += 1
                except Try7zError:
                    failed_indices.append(idx + 1)  # Record 1-based for warning

            # Report warnings in original order
            for idx in sorted(failed_indices):
                print(f"Warning: Index {idx} out of range", file=sys.stderr)

            print(f"Removed {removed_count} password(s). Total: {manager.count()}")
        else:
            # Remove by password value
            removed_count = 0
            failed_passwords = []

            for password in args.password:
                try:
                    manager.remove_password(password)
                    print(f"  Removed: {password}")
                    removed_count += 1
                except Try7zError:
                    failed_passwords.append(password)

            # Report warnings
            for password in failed_passwords:
                print(f"Warning: Password '{password}' not found", file=sys.stderr)

            print(f"Removed {removed_count} password(s). Total: {manager.count()}")

        return 0

    except Try7zError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


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
        manager = PasswordManager()
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
        manager = PasswordManager()
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
        manager = PasswordManager()
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
        manager = PasswordManager()
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


def _extract_single(
    archive_path: Path,
    output_dir: Path,
    passwords: list[str],
    force: bool,
) -> int:
    """Extract a single archive and return exit code."""
    try:
        extractor = Extractor(archive_path)
    except Try7zError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Check if output directory exists
    if output_dir.exists():
        item_type = "directory" if output_dir.is_dir() else "file"
        if force:
            print(
                f"Warning: Output {item_type} '{output_dir.name}' already exists "
                "and will be overwritten."
            )
        else:
            confirm = input(
                f"Output {item_type} '{output_dir.name}' already exists. Overwrite? [y/N]: "
            )
            if confirm.lower() != "y":
                print("Extraction cancelled.")
                return 1

            # Remove existing directory/file
            if output_dir.is_dir():
                shutil.rmtree(output_dir)
            else:
                output_dir.unlink()

    print(f"Attempting to extract: {archive_path.name}")
    print(f"Trying {len(passwords)} password(s)...")

    try:
        success, used_password = extractor.extract_with_passwords(
            passwords, output_dir, show_progress=True, show_password_progress=True
        )

        if success:
            if used_password:
                print("Success! Extracted with password.")
            else:
                print("Success! Archive was not password-protected.")

            print(f"Extracted to: {output_dir}")
            return 0
        else:
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
        manager = PasswordManager()
    passwords = manager.get_passwords()

    if args.password:
        passwords = [args.password] + passwords

    success_count = 0
    failure_count = 0
    total = len(args.archive)

    for archive_str in args.archive:
        archive_path = Path(archive_str)

        # Determine output directory
        if args.output:
            if total > 1:
                output_dir = Path(args.output) / archive_path.stem
            else:
                output_dir = Path(args.output)
        else:
            output_dir = archive_path.parent / archive_path.stem
        output_dir = output_dir.resolve()

        result = _extract_single(archive_path, output_dir, passwords, args.force)
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
