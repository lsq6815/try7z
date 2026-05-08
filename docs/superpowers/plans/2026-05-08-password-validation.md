# Password Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add pluggable password validation to reject empty, whitespace-only, and overly long passwords.

**Architecture:** Strategy pattern with PasswordValidator ABC and BasicPasswordValidator implementation. PasswordManager accepts optional validator parameter.

**Tech Stack:** Python 3.10+, abc module, pytest

---

## File Structure

**Modified:**
- `try7z/utils.py` - Add PasswordValidator ABC, BasicPasswordValidator, PasswordValidationError
- `try7z/password_manager.py` - Modify add_password() signature
- `try7z/main.py` - Add PasswordValidationError handling
- `tests/test_utils.py` - Add validator tests
- `tests/test_password_manager.py` - Add validation integration tests, update edge case tests
- `tests/test_cli.py` - Add CLI validation tests

---

## Task 1: Add PasswordValidator ABC and BasicPasswordValidator

**Files:**
- Modify: `try7z/utils.py:1-280`

- [ ] **Step 1: Write the failing test for BasicPasswordValidator empty string**

```python
# In tests/test_utils.py, add new test class at the end

class TestBasicPasswordValidator:
    """Test cases for BasicPasswordValidator."""

    def test_validate_empty_string(self) -> None:
        """Test that empty string raises PasswordValidationError."""
        from try7z.utils import BasicPasswordValidator, PasswordValidationError
        
        validator = BasicPasswordValidator()
        with pytest.raises(PasswordValidationError, match="cannot be empty"):
            validator.validate("")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_utils.py::TestBasicPasswordValidator::test_validate_empty_string -v`
Expected: FAIL with "cannot import name 'BasicPasswordValidator'"

- [ ] **Step 3: Add imports and PasswordValidator ABC to utils.py**

```python
# In try7z/utils.py, add to imports at line 36:
from abc import ABC, abstractmethod

# Add after Try7zError class (after line 55):
class PasswordValidationError(Try7zError):
    """Exception raised when password validation fails.
    
    This exception indicates that a password does not meet
    the required validation criteria.
    
    Example:
        >>> from try7z.utils import BasicPasswordValidator, PasswordValidationError
        >>> validator = BasicPasswordValidator()
        >>> try:
        ...     validator.validate("")
        ... except PasswordValidationError as e:
        ...     print(e)  # "Password cannot be empty"
    """
    pass


class PasswordValidator(ABC):
    """Abstract base class for password validation strategies.
    
    Implementations define specific validation rules by implementing
    the validate() method.
    
    Example:
        >>> from try7z.utils import PasswordValidator, PasswordValidationError
        >>> class CustomValidator(PasswordValidator):
        ...     def validate(self, password: str) -> None:
        ...         if len(password) < 5:
        ...             raise PasswordValidationError("Too short")
    """
    
    @abstractmethod
    def validate(self, password: str) -> None:
        """Validate password against implementation-specific rules.
        
        Args:
            password: Password string to validate.
            
        Raises:
            PasswordValidationError: If password fails validation.
        """
        pass


class BasicPasswordValidator(PasswordValidator):
    """Basic password validator with common validation rules.
    
    Validates:
        - Password is not empty
        - Password is not whitespace-only
        - Password length does not exceed MAX_LENGTH
    
    Attributes:
        MAX_LENGTH: Maximum allowed password length (1000 characters).
    
    Example:
        >>> from try7z.utils import BasicPasswordValidator, PasswordValidationError
        >>> validator = BasicPasswordValidator()
        >>> validator.validate("valid_password")  # No exception raised
        >>> try:
        ...     validator.validate("")
        ... except PasswordValidationError:
        ...     print("Invalid password")
    """
    
    MAX_LENGTH = 1000
    
    def validate(self, password: str) -> None:
        """Validate password against basic rules.
        
        Args:
            password: Password string to validate.
            
        Raises:
            PasswordValidationError: If password is empty, whitespace-only,
                                    or exceeds MAX_LENGTH.
        """
        if not password:
            raise PasswordValidationError("Password cannot be empty")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_utils.py::TestBasicPasswordValidator::test_validate_empty_string -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add try7z/utils.py tests/test_utils.py
git commit -m "feat: add PasswordValidator ABC and BasicPasswordValidator with empty check"
```

---

## Task 2: Add whitespace and max length validation

**Files:**
- Modify: `try7z/utils.py`
- Modify: `tests/test_utils.py`

- [ ] **Step 1: Write the failing tests for whitespace-only passwords**

```python
# In tests/test_utils.py, add to TestBasicPasswordValidator class:

    def test_validate_whitespace_only(self) -> None:
        """Test that whitespace-only password raises error."""
        from try7z.utils import BasicPasswordValidator, PasswordValidationError
        
        validator = BasicPasswordValidator()
        with pytest.raises(PasswordValidationError, match="whitespace-only"):
            validator.validate("   ")
        
    def test_validate_whitespace_tabs_newlines(self) -> None:
        """Test that mixed whitespace raises error."""
        from try7z.utils import BasicPasswordValidator, PasswordValidationError
        
        validator = BasicPasswordValidator()
        with pytest.raises(PasswordValidationError, match="whitespace-only"):
            validator.validate("  \t\n  ")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_utils.py::TestBasicPasswordValidator::test_validate_whitespace_only -v`
Expected: FAIL with "Password cannot be empty" (wrong error message)

- [ ] **Step 3: Add whitespace validation to BasicPasswordValidator.validate()**

```python
# In try7z/utils.py, in BasicPasswordValidator.validate(), after empty check:
        if not password:
            raise PasswordValidationError("Password cannot be empty")
        if password.isspace():
            raise PasswordValidationError("Password cannot be whitespace-only")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_utils.py::TestBasicPasswordValidator -v`
Expected: All PASS

- [ ] **Step 5: Write the failing tests for max length**

```python
# In tests/test_utils.py, add to TestBasicPasswordValidator class:

    def test_validate_max_length_exceeded(self) -> None:
        """Test that password exceeding max length raises error."""
        from try7z.utils import BasicPasswordValidator, PasswordValidationError
        
        validator = BasicPasswordValidator()
        long_password = "a" * 1001
        with pytest.raises(PasswordValidationError, match="exceeds maximum length"):
            validator.validate(long_password)
    
    def test_validate_max_length_exactly_1000(self) -> None:
        """Test that password exactly 1000 chars is valid."""
        from try7z.utils import BasicPasswordValidator
        
        validator = BasicPasswordValidator()
        password_1000 = "a" * 1000
        validator.validate(password_1000)  # Should not raise
    
    def test_validate_valid_password(self) -> None:
        """Test that valid password passes validation."""
        from try7z.utils import BasicPasswordValidator
        
        validator = BasicPasswordValidator()
        validator.validate("valid_password123")  # Should not raise
```

- [ ] **Step 6: Run tests to verify they fail**

Run: `pytest tests/test_utils.py::TestBasicPasswordValidator::test_validate_max_length_exceeded -v`
Expected: FAIL (no max length check yet)

- [ ] **Step 7: Add max length validation to BasicPasswordValidator.validate()**

```python
# In try7z/utils.py, in BasicPasswordValidator.validate(), after whitespace check:
        if password.isspace():
            raise PasswordValidationError("Password cannot be whitespace-only")
        if len(password) > self.MAX_LENGTH:
            raise PasswordValidationError(
                f"Password exceeds maximum length of {self.MAX_LENGTH} characters"
            )
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `pytest tests/test_utils.py::TestBasicPasswordValidator -v`
Expected: All PASS

- [ ] **Step 9: Update imports in test_utils.py**

```python
# In tests/test_utils.py, update the imports at the top (line 9):
from try7z.utils import (
    SUPPORTED_EXTENSIONS,
    BasicPasswordValidator,
    InvalidArchiveError,
    PasswordValidationError,
    PasswordValidator,
    get_package_root,
    get_supported_extensions,
    get_user_data_dir,
    is_supported_archive,
    validate_archive_path,
)
```

- [ ] **Step 10: Update test methods to use imported classes**

```python
# In tests/test_utils.py, update test methods in TestBasicPasswordValidator to remove inline imports:

    def test_validate_empty_string(self) -> None:
        """Test that empty string raises PasswordValidationError."""
        validator = BasicPasswordValidator()
        with pytest.raises(PasswordValidationError, match="cannot be empty"):
            validator.validate("")
            
    def test_validate_whitespace_only(self) -> None:
        """Test that whitespace-only password raises error."""
        validator = BasicPasswordValidator()
        with pytest.raises(PasswordValidationError, match="whitespace-only"):
            validator.validate("   ")
        
    def test_validate_whitespace_tabs_newlines(self) -> None:
        """Test that mixed whitespace raises error."""
        validator = BasicPasswordValidator()
        with pytest.raises(PasswordValidationError, match="whitespace-only"):
            validator.validate("  \t\n  ")
    
    def test_validate_max_length_exceeded(self) -> None:
        """Test that password exceeding max length raises error."""
        validator = BasicPasswordValidator()
        long_password = "a" * 1001
        with pytest.raises(PasswordValidationError, match="exceeds maximum length"):
            validator.validate(long_password)
    
    def test_validate_max_length_exactly_1000(self) -> None:
        """Test that password exactly 1000 chars is valid."""
        validator = BasicPasswordValidator()
        password_1000 = "a" * 1000
        validator.validate(password_1000)  # Should not raise
    
    def test_validate_valid_password(self) -> None:
        """Test that valid password passes validation."""
        validator = BasicPasswordValidator()
        validator.validate("valid_password123")  # Should not raise
```

- [ ] **Step 11: Run all BasicPasswordValidator tests**

Run: `pytest tests/test_utils.py::TestBasicPasswordValidator -v`
Expected: All PASS

- [ ] **Step 12: Commit**

```bash
git add try7z/utils.py tests/test_utils.py
git commit -m "feat: add whitespace and max length validation to BasicPasswordValidator"
```

---

## Task 3: Integrate validator into PasswordManager.add_password()

**Files:**
- Modify: `try7z/password_manager.py:180-206`
- Modify: `tests/test_password_manager.py`

- [ ] **Step 1: Write the failing test for validator integration**

```python
# In tests/test_password_manager.py, update imports at line 10:
from try7z.utils import PasswordManagerError, PasswordValidationError

# Update existing edge case tests to expect validation errors:
    def test_add_empty_string_password(self, manager: PasswordManager) -> None:
        """Test adding empty string password now raises validation error."""
        with pytest.raises(PasswordValidationError, match="cannot be empty"):
            manager.add_password("")

    def test_add_whitespace_only_password(self, manager: PasswordManager) -> None:
        """Test adding whitespace-only password now raises validation error."""
        with pytest.raises(PasswordValidationError, match="whitespace-only"):
            manager.add_password("   ")

    def test_add_very_long_password(self, manager: PasswordManager) -> None:
        """Test adding very long password now raises validation error."""
        long_pwd = "a" * 10001
        with pytest.raises(PasswordValidationError, match="exceeds maximum length"):
            manager.add_password(long_pwd)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_password_manager.py::TestEdgeCases -v`
Expected: FAIL (validation not yet implemented)

- [ ] **Step 3: Add validator parameter to PasswordManager.add_password()**

```python
# In try7z/password_manager.py, update imports at line 56:
from try7z.utils import (
    PasswordManagerError,
    get_user_data_dir,
)
from try7z.utils import BasicPasswordValidator, PasswordValidator

# Update add_password method (lines 180-206):
    def add_password(
        self, 
        password: str, 
        validator: PasswordValidator | None = None
    ) -> None:
        """Add a password to the list.
        
        Adds a new password to the stored list and saves to disk.
        Duplicate passwords are not allowed.
        
        Args:
            password: The password string to add.
            validator: Optional validator instance. If None, uses
                      BasicPasswordValidator().
        
        Raises:
            PasswordValidationError: If password validation fails.
            PasswordManagerError: If the password already exists in the list.
        
        Example:
            >>> pm = PasswordManager()
            >>> pm.add_password("mysecret")
            >>> pm.count()
            1
            >>> pm.add_password("mysecret")  # Raises error
            Traceback (most recent call last):
                ...
            try7z.utils.PasswordManagerError: Password already exists
        """
        if validator is None:
            validator = BasicPasswordValidator()
        
        validator.validate(password)
        
        if password in self._passwords:
            raise PasswordManagerError("Password already exists")
        
        self._passwords.append(password)
        self._save_passwords()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_password_manager.py::TestEdgeCases -v`
Expected: All PASS

- [ ] **Step 5: Write test for custom validator**

```python
# In tests/test_password_manager.py, add new test class:

class TestPasswordManagerWithValidator:
    """Test cases for PasswordManager with custom validators."""

    def test_add_password_with_custom_validator(
        self, manager: PasswordManager
    ) -> None:
        """Test adding password with custom validator."""
        from try7z.utils import PasswordValidator, PasswordValidationError
        
        class MinLengthValidator(PasswordValidator):
            def __init__(self, min_length: int = 5):
                self.min_length = min_length
            
            def validate(self, password: str) -> None:
                if len(password) < self.min_length:
                    raise PasswordValidationError(
                        f"Password must be at least {self.min_length} characters"
                    )
        
        # Short password should fail with custom validator
        with pytest.raises(PasswordValidationError, match="at least 5"):
            manager.add_password("abc", validator=MinLengthValidator())
        
        # Valid password should pass
        manager.add_password("abcdef", validator=MinLengthValidator())
        assert "abcdef" in manager.get_passwords()
    
    def test_add_password_default_uses_basic_validator(
        self, manager: PasswordManager
    ) -> None:
        """Test that default validator is BasicPasswordValidator."""
        # Empty string should be rejected by default
        with pytest.raises(PasswordValidationError, match="cannot be empty"):
            manager.add_password("")
```

- [ ] **Step 6: Run new tests**

Run: `pytest tests/test_password_manager.py::TestPasswordManagerWithValidator -v`
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add try7z/password_manager.py tests/test_password_manager.py
git commit -m "feat: integrate PasswordValidator into PasswordManager.add_password()"
```

---

## Task 4: Add CLI validation error handling

**Files:**
- Modify: `try7z/main.py:68-119`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write the failing tests for CLI validation**

```python
# In tests/test_cli.py, update imports at line 10:
from try7z.main import (
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
from try7z.password_manager import PasswordManager

# Add new test methods to TestAddCommand class:
    def test_add_empty_password_shows_warning(
        self, password_manager: PasswordManager, capsys
    ) -> None:
        """Test that empty password is skipped with warning."""
        args = argparse.Namespace()
        args.passwords = ["", "valid"]

        exit_code = cmd_add_password(args, password_manager)

        assert exit_code == 0
        assert password_manager.count() == 1
        assert "valid" in password_manager.get_passwords()
        captured = capsys.readouterr()
        assert "cannot be empty" in captured.err
        assert "skipped" in captured.err.lower()

    def test_add_whitespace_password_shows_warning(
        self, password_manager: PasswordManager, capsys
    ) -> None:
        """Test that whitespace-only password is skipped."""
        args = argparse.Namespace()
        args.passwords = ["   ", "valid"]

        exit_code = cmd_add_password(args, password_manager)

        assert exit_code == 0
        assert password_manager.count() == 1
        captured = capsys.readouterr()
        assert "whitespace-only" in captured.err

    def test_add_very_long_password_shows_warning(
        self, password_manager: PasswordManager, capsys
    ) -> None:
        """Test that very long password is skipped."""
        args = argparse.Namespace()
        args.passwords = ["a" * 1001, "valid"]

        exit_code = cmd_add_password(args, password_manager)

        assert exit_code == 0
        assert password_manager.count() == 1
        captured = capsys.readouterr()
        assert "exceeds maximum length" in captured.err

    def test_add_mixed_valid_invalid_and_duplicate(
        self, password_manager: PasswordManager, capsys
    ) -> None:
        """Test batch with valid, invalid, and duplicate passwords."""
        password_manager.add_password("existing")

        args = argparse.Namespace()
        args.passwords = ["", "existing", "valid", "   ", "another"]

        exit_code = cmd_add_password(args, password_manager)

        assert exit_code == 0
        assert password_manager.count() == 3  # existing + valid + another
        captured = capsys.readouterr()
        assert "Added 2 password(s)" in captured.out
        assert "Skipped 3" in captured.out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cli.py::TestAddCommand::test_add_empty_password_shows_warning -v`
Expected: FAIL (PasswordValidationError not caught)

- [ ] **Step 3: Update cmd_add_password() to catch PasswordValidationError**

```python
# In try7z/main.py, update imports at line 65:
from try7z.utils import PasswordNotFoundError, PasswordValidationError, Try7zError

# Update cmd_add_password() (lines 68-119):
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
        manager = PasswordManager()

    added_count = 0
    skipped_count = 0
    added_passwords: list[str] = []

    for password in args.passwords:
        try:
            manager.add_password(password)
            added_count += 1
            added_passwords.append(password)
        except PasswordValidationError as e:
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

    return 0 if added_count > 0 else 1
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cli.py::TestAddCommand -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add try7z/main.py tests/test_cli.py
git commit -m "feat: add PasswordValidationError handling to CLI"
```

---

## Task 5: Run full test suite and verify

**Files:**
- All modified files

- [ ] **Step 1: Run all tests**

Run: `pytest tests/ -v`
Expected: All PASS

- [ ] **Step 2: Run ruff linter**

Run: `ruff check .`
Expected: No errors

- [ ] **Step 3: Run mypy type checker**

Run: `mypy try7z/`
Expected: Success: no issues found

- [ ] **Step 4: Final commit (if any fixes needed)**

```bash
git add .
git commit -m "fix: resolve linting and type checking issues"
```

- [ ] **Step 5: Verify implementation matches spec**

Review that all requirements are met:
- [x] PasswordValidator ABC with validate() method
- [x] BasicPasswordValidator with empty, whitespace, max length checks
- [x] PasswordValidationError exception
- [x] PasswordManager.add_password() accepts optional validator
- [x] CLI catches PasswordValidationError and shows warning
- [x] Invalid passwords are skipped, processing continues
- [x] Tests cover all new functionality

---

## Summary

This implementation adds pluggable password validation with:
- Abstract base class for custom validators
- Basic validator with common checks
- Integration into PasswordManager with backward compatibility
- CLI error handling that matches existing duplicate behavior
- Comprehensive test coverage
