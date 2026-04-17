"""CLI entry point for AutoPassTryUnzip."""

import argparse
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from autopasstryunzip.extractor import Extractor
from autopasstryunzip.password_manager import PasswordManager
from autopasstryunzip.utils import AutoPassError, PasswordNotFoundError


def cmd_add_password(
    args: argparse.Namespace,
    manager: PasswordManager | None = None,
) -> int:
    """Add password(s) to the list.

    Args:
        args: Parsed command line arguments.
        manager: Optional PasswordManager instance for testing.

    Returns:
        Exit code.
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

    Args:
        args: Parsed command line arguments.
        manager: Optional PasswordManager instance for testing.

    Returns:
        Exit code.
    """
    if manager is None:
        manager = PasswordManager()

    # 验证：不能同时使用两种方式
    if args.password and args.index:
        print("Error: Cannot use both password value and --index", file=sys.stderr)
        return 1

    # 验证：至少使用一种方式
    if not args.password and not args.index:
        print("Error: Please specify password(s) or use --index", file=sys.stderr)
        return 1

    try:
        if args.index:
            # 处理下标删除
            # 去重并保持输入顺序
            seen = set()
            unique_indices = []
            for idx in args.index:
                if idx not in seen:
                    seen.add(idx)
                    unique_indices.append(idx)

            # 转换为 0-based 并排序（从大到小，避免删除后索引变化）
            indices_0based = sorted([i - 1 for i in unique_indices], reverse=True)

            removed_count = 0
            failed_indices = []

            for idx in indices_0based:
                try:
                    removed_pw = manager.remove_by_index(idx)
                    print(f"  Removed [{idx + 1}]: {removed_pw}")
                    removed_count += 1
                except AutoPassError:
                    failed_indices.append(idx + 1)  # 记录 1-based 用于警告

            # 报告警告（按原始顺序）
            for idx in sorted(failed_indices):
                print(f"Warning: Index {idx} out of range", file=sys.stderr)

            print(f"Removed {removed_count} password(s). Total: {manager.count()}")
        else:
            # 按密码值删除（支持多个）
            removed_count = 0
            failed_passwords = []

            for password in args.password:
                try:
                    manager.remove_password(password)
                    print(f"  Removed: {password}")
                    removed_count += 1
                except AutoPassError:
                    failed_passwords.append(password)

            # 报告警告
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
    """List all stored passwords.

    Args:
        args: Parsed command line arguments.
        manager: Optional PasswordManager instance for testing.

    Returns:
        Exit code.
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

    Args:
        args: Parsed command line arguments.
        manager: Optional PasswordManager instance for testing.

    Returns:
        Exit code.
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
    """Show passwords file path.

    Args:
        args: Parsed command line arguments.
        manager: Optional PasswordManager instance for testing.

    Returns:
        Exit code.
    """
    if manager is None:
        manager = PasswordManager()
    print(manager.passwords_file)
    return 0


def cmd_edit_passwords(args: argparse.Namespace) -> int:
    """Open passwords file in default editor.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code.
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

    if args.command is None:
        parser.print_help()
        return 0

    func: Callable[[argparse.Namespace], int] = args.func
    return func(args)


if __name__ == "__main__":
    sys.exit(main())
