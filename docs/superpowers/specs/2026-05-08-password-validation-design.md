# Password Validation Design

## Overview

Add input validation for the `add_password` functionality using a pluggable validator pattern. This design provides extensibility for future validation rules while keeping the current implementation simple.

## Requirements

### Current Validation Rules
- Block empty strings
- Block whitespace-only strings
- Block passwords exceeding 1000 characters

### Behavior on Validation Failure
- Skip invalid passwords with warning
- Continue processing remaining passwords (consistent with duplicate handling)

## Architecture

### Components

1. **PasswordValidator (ABC)** - Abstract base class defining the validation interface
2. **BasicPasswordValidator** - Concrete implementation with current validation rules
3. **PasswordValidationError** - Exception for validation failures
4. **PasswordManager.add_password()** - Modified to accept optional validator parameter
5. **CLI cmd_add_password()** - Catches validation errors and displays warnings

### Design Pattern

Strategy Pattern - allows validation logic to be swapped at runtime without modifying PasswordManager.

## Implementation Details

### 1. PasswordValidator Interface (utils.py)

```python
from abc import ABC, abstractmethod

class PasswordValidator(ABC):
    """Abstract base class for password validation strategies."""
    
    @abstractmethod
    def validate(self, password: str) -> None:
        """
        Validate password against rules.
        
        Args:
            password: Password string to validate
            
        Raises:
            PasswordValidationError: If password fails validation
        """
        pass

class BasicPasswordValidator(PasswordValidator):
    """Basic validator: empty, whitespace, max length checks."""
    
    MAX_LENGTH = 1000
    
    def validate(self, password: str) -> None:
        if not password:
            raise PasswordValidationError("Password cannot be empty")
        if password.isspace():
            raise PasswordValidationError("Password cannot be whitespace-only")
        if len(password) > self.MAX_LENGTH:
            raise PasswordValidationError(
                f"Password exceeds maximum length of {self.MAX_LENGTH} characters"
            )

class PasswordValidationError(Try7zError):
    """Exception raised when password validation fails."""
    pass
```

### 2. PasswordManager Integration (password_manager.py)

Modify `add_password()` signature:

```python
def add_password(
    self, 
    password: str, 
    validator: PasswordValidator | None = None
) -> None:
    """
    Add a password to the list.
    
    Args:
        password: The password string to add
        validator: Optional validator instance. If None, uses BasicPasswordValidator()
        
    Raises:
        PasswordValidationError: Password validation failed
        PasswordManagerError: Password already exists
    """
    if validator is None:
        validator = BasicPasswordValidator()
    
    validator.validate(password)
    
    if password in self._passwords:
        raise PasswordManagerError("Password already exists")
    
    self._passwords.append(password)
    self._save_passwords()
```

### 3. CLI Integration (main.py)

Update `cmd_add_password()` to catch `PasswordValidationError`:

```python
from try7z.utils import PasswordValidationError

def cmd_add_password(
    args: argparse.Namespace,
    manager: PasswordManager | None = None,
) -> int:
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
    
    # ... existing output logic ...
```

## Extensibility

### Adding New Validators

Create new validator by inheriting from `PasswordValidator`:

```python
class StrictPasswordValidator(PasswordValidator):
    """Extended validation: basic rules + min length + no control chars."""
    
    MIN_LENGTH = 8
    MAX_LENGTH = 1000
    
    def validate(self, password: str) -> None:
        # Reuse basic validation
        BasicPasswordValidator().validate(password)
        
        # Add extended rules
        if len(password) < self.MIN_LENGTH:
            raise PasswordValidationError(
                f"Password must be at least {self.MIN_LENGTH} characters"
            )
        
        if any(ord(c) < 32 for c in password):
            raise PasswordValidationError("Password contains control characters")
```

### Usage Examples

```python
# Default validation (BasicPasswordValidator)
manager.add_password("my_password")

# Custom validation
manager.add_password("pwd123", validator=StrictPasswordValidator())

# Disable validation for testing (requires NoOpValidator - future enhancement)
# manager.add_password("test", validator=NoOpValidator())
```

## Testing Strategy

### Unit Tests

1. **test_BasicPasswordValidator**
   - Test empty string rejection
   - Test whitespace-only rejection
   - Test max length enforcement
   - Test valid passwords pass

2. **test_PasswordManager_with_validator**
   - Test default validator behavior
   - Test custom validator injection
   - Test validation error handling

3. **test_cmd_add_password_validation**
   - Test warning output for invalid passwords
   - Test batch processing with mixed valid/invalid
   - Test exit code with all invalid

### Integration Tests

- End-to-end CLI validation with various inputs

## Backward Compatibility

- Existing code without validator parameter continues to work (uses default BasicPasswordValidator)
- No breaking changes to public API
- Exception hierarchy maintains Try7zError as base

## Future Enhancements

Potential validators to add:
- `MinLengthValidator` - enforce minimum password length
- `ControlCharacterValidator` - reject control characters (newline, tab, etc.)
- `CharacterSetValidator` - restrict to specific character sets
- `CompositeValidator` - combine multiple validators
- `NoOpValidator` - disable validation for specific use cases

## Files Modified

- `try7z/utils.py` - Add PasswordValidator ABC, BasicPasswordValidator, PasswordValidationError
- `try7z/password_manager.py` - Modify add_password() signature and implementation
- `try7z/main.py` - Update cmd_add_password() error handling
- `tests/test_utils.py` - Add validator unit tests
- `tests/test_password_manager.py` - Add validation integration tests
- `tests/test_main.py` - Add CLI validation tests
