"""CLI entry point and command handlers for AutoPassTryUnzip.

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

Usage:
    Basic command structure::

        $ autopass-unzip <command> [options]

    Examples::

        $ autopass-unzip add "mypassword"
        $ autopass-unzip add "pwd1" "pwd2" "pwd3"
        $ autopass-unzip list
        $ autopass-unzip remove -i 2 3
        $ autopass-unzip extract archive.7z -o output_dir

    See individual command help::

        $ autopass-unzip <command> --help

Exit Codes:
    0: Success
    1: Error (invalid arguments, operation failed, etc.)

Example:
    Using argparse.Namespace for testing::

        >>> import argparse
        >>> from autopasstryunzip.main import cmd_list_passwords
        >>>
        >>> args = argparse.Namespace()
        >>> exit_code = cmd_list_passwords(args)
"""

import argparse
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from autopasstryunzip import __version__
from autopasstryunzip.extractor import Extractor, get_7z_version
from autopasstryunzip.password_manager import PasswordManager
from autopasstryunzip.utils import AutoPassError, PasswordNotFoundError


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

    for password in args.passwords:
        try:
            manager.add_password(password)
            added_count += 1
        except AutoPassError:
            print(f"Warning: Password '{password}' already exists", file=sys.stderr)
            skipped_count += 1

    if added_count > 0:
        print(f"Added {added_count} password(s). Total: {manager.count()}")
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
                except AutoPassError:
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
                except AutoPassError:
                    failed_passwords.append(password)

            # Report warnings
            for password in failed_passwords:
                print(f"Warning: Password '{password}' not found", file=sys.stderr)

            print(f"Removed {removed_count} password(s). Total: {manager.count()}")

        return 0

    except AutoPassError as e:
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
    for i, pw in enumerate(passwords, 1):
        print(f"  {i}. {pw}")

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
        C:\\Users\\Username\\AppData\\Roaming\\autoPassTryUnzip\\passwords.json
        0
    """
    if manager is None:
        manager = PasswordManager()
    print(manager.passwords_file)
    return 0


def cmd_edit_passwords(args: argparse.Namespace) -> int:
    """Open passwords file in the default system editor.

    Opens the passwords.json file using the system's default
    application for JSON files. Creates the file if it doesn't exist.

    Args:
        args: Parsed command line arguments (no specific attributes used).

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


def cmd_extract(args: argparse.Namespace) -> int:
    """Extract an archive using stored passwords.

    Extracts a password-protected archive by trying all stored
    passwords (plus an optional additional password). Reports
    success or failure to the user.

    Args:
        args: Parsed command line arguments. Expected attributes:
            - archive: Path to the archive file
            - output: Optional output directory path
            - password: Optional additional password to try first

    Returns:
        Exit code (0 on success, 1 on error).

    Example:
        Basic extraction::

            >>> args = argparse.Namespace()
            >>> args.archive = "secret.7z"
            >>> args.output = None
            >>> args.password = None
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
    archive_path = Path(args.archive)

    try:
        extractor = Extractor(archive_path)
    except AutoPassError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    manager = PasswordManager()
    passwords = manager.get_passwords()

    if args.password:
        passwords = [args.password] + passwords

    output_dir = Path(args.output) if args.output else None

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

            if output_dir:
                print(f"Extracted to: {output_dir}")
            else:
                print(f"Extracted to: {archive_path.parent / archive_path.stem}")

            return 0
        else:
            print("Extraction failed.", file=sys.stderr)
            return 1

    except PasswordNotFoundError:
        print("No matching password found", file=sys.stderr)
        return 1
    except AutoPassError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main() -> int:
    """Main entry point for the CLI application.

    Parses command-line arguments and dispatches to the appropriate
    handler function. Supports --version and --help flags.

    Returns:
        Exit code from the executed command.

    Example:
        Command-line usage::

            $ autopass-unzip --version
            $ autopass-unzip --help
            $ autopass-unzip add "password"
            $ autopass-unzip extract archive.7z
    """
    parser = argparse.ArgumentParser(
        prog="autopass-unzip",
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

    extract_parser = subparsers.add_parser("extract", help="Extract an archive")
    extract_parser.add_argument("archive", help="Path to archive file")
    extract_parser.add_argument("-o", "--output", help="Output directory")
    extract_parser.add_argument("-p", "--password", help="Additional password to try first")
    extract_parser.set_defaults(func=cmd_extract)

    args = parser.parse_args()

    if args.version:
        print(f"autopasstryunzip {__version__}")
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
