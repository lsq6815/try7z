"""CLI entry point for AutoPassTryUnzip."""

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

from autopasstryunzip.extractor import Extractor
from autopasstryunzip.password_manager import PasswordManager
from autopasstryunzip.utils import AutoPassError, PasswordNotFoundError


def cmd_add_password(args: argparse.Namespace) -> int:
    """Add a password to the password list.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code.
    """
    manager = PasswordManager()

    try:
        manager.add_password(args.password)
        print(f"Password added. Total: {manager.count()}")
        return 0
    except AutoPassError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_remove_password(args: argparse.Namespace) -> int:
    """Remove a password from the password list.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code.
    """
    manager = PasswordManager()

    try:
        manager.remove_password(args.password)
        print(f"Password removed. Total: {manager.count()}")
        return 0
    except AutoPassError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_list_passwords(args: argparse.Namespace) -> int:
    """List all stored passwords.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code.
    """
    manager = PasswordManager()
    passwords = manager.get_passwords()

    if not passwords:
        print("No passwords stored.")
        return 0

    print(f"Stored passwords ({manager.count()}):")
    for i, pw in enumerate(passwords, 1):
        print(f"  {i}. {pw}")

    return 0


def cmd_clear_passwords(args: argparse.Namespace) -> int:
    """Clear all stored passwords.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code.
    """
    if not args.force:
        confirm = input("Clear all passwords? [y/N]: ")
        if confirm.lower() != "y":
            print("Cancelled.")
            return 0

    manager = PasswordManager()
    manager.clear_passwords()
    print("All passwords cleared.")
    return 0


def cmd_extract(args: argparse.Namespace) -> int:
    """Extract an archive using stored passwords.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code.
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
        success, used_password = extractor.extract_with_passwords(passwords, output_dir)

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
        print("Error: No matching password found.", file=sys.stderr)
        return 1
    except AutoPassError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main() -> int:
    """Main entry point.

    Returns:
        Exit code.
    """
    parser = argparse.ArgumentParser(
        prog="autopass-unzip",
        description="Auto-extract password-protected archives",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    add_parser = subparsers.add_parser("add", help="Add a password")
    add_parser.add_argument("password", help="Password to add")
    add_parser.set_defaults(func=cmd_add_password)

    remove_parser = subparsers.add_parser("remove", help="Remove a password")
    remove_parser.add_argument("password", help="Password to remove")
    remove_parser.set_defaults(func=cmd_remove_password)

    list_parser = subparsers.add_parser("list", help="List stored passwords")
    list_parser.set_defaults(func=cmd_list_passwords)

    clear_parser = subparsers.add_parser("clear", help="Clear all passwords")
    clear_parser.add_argument("-f", "--force", action="store_true", help="Skip confirmation")
    clear_parser.set_defaults(func=cmd_clear_passwords)

    extract_parser = subparsers.add_parser("extract", help="Extract an archive")
    extract_parser.add_argument("archive", help="Path to archive file")
    extract_parser.add_argument("-o", "--output", help="Output directory")
    extract_parser.add_argument("-p", "--password", help="Additional password to try first")
    extract_parser.set_defaults(func=cmd_extract)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    func: Callable[[argparse.Namespace], int] = args.func
    return func(args)


if __name__ == "__main__":
    sys.exit(main())
