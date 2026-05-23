"""Tests for Extractor."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from try7z.extractor import (
    Extractor,
    _compute_skip_depth,
    _flatten_and_move,
    get_7z_path,
    get_7z_version,
)
from try7z.utils import ExtractionError, InvalidArchiveError, PasswordNotFoundError


@pytest.fixture
def plain_zip_archive(temp_dir: Path, seven_zip: Path) -> Path:
    """Create a plain (non-encrypted) zip archive for testing."""
    src_dir = temp_dir / "src"
    src_dir.mkdir()
    (src_dir / "test.txt").write_text("Hello, ZIP!")

    archive_path = temp_dir / "plain.zip"
    subprocess.run(
        [str(seven_zip), "a", str(archive_path), str(src_dir)],
        capture_output=True,
        check=True,
    )
    return archive_path


@pytest.fixture
def encrypted_zip_archive(temp_dir: Path, seven_zip: Path) -> Path:
    """Create an encrypted zip archive for testing."""
    src_dir = temp_dir / "src"
    src_dir.mkdir()
    (src_dir / "test.txt").write_text("Secret ZIP content!")

    archive_path = temp_dir / "encrypted.zip"
    subprocess.run(
        [str(seven_zip), "a", "-pzipsecret", str(archive_path), str(src_dir)],
        capture_output=True,
        check=True,
    )
    return archive_path


class TestExtractor:
    """Test cases for Extractor."""

    def test_init_with_valid_archive(self, plain_7z_archive: Path) -> None:
        """Test initialization with valid archive."""
        extractor = Extractor(plain_7z_archive)
        assert extractor.archive_path == plain_7z_archive.resolve()

    def test_init_with_nonexistent_file(self, temp_dir: Path) -> None:
        """Test that nonexistent file raises error."""
        with pytest.raises(InvalidArchiveError, match="not found"):
            Extractor(temp_dir / "nonexistent.7z")

    def test_init_with_unsupported_format(self, temp_dir: Path) -> None:
        """Test that unsupported format raises error."""
        unsupported_file = temp_dir / "test.xyz"
        unsupported_file.write_text("not an archive")
        with pytest.raises(InvalidArchiveError, match="Unsupported"):
            Extractor(unsupported_file)

    def test_extract_plain_7z_archive(self, plain_7z_archive: Path, temp_dir: Path) -> None:
        """Test extracting a plain 7z archive."""
        extractor = Extractor(plain_7z_archive)
        output_dir = temp_dir / "output"

        success, password = extractor.try_extract(output_dir)

        assert success is True
        assert password is None
        assert (output_dir / "src" / "test.txt").exists()

    def test_extract_encrypted_7z_with_password_list(
        self, encrypted_7z_archive: Path, temp_dir: Path
    ) -> None:
        """Test extracting encrypted 7z with a list of passwords."""
        extractor = Extractor(encrypted_7z_archive)
        output_dir = temp_dir / "output"
        passwords = ["wrong1", "wrong2", "secret123", "wrong3"]

        success, used_password = extractor.try_extract(output_dir, passwords)

        assert success is True
        assert used_password == "secret123"
        assert (output_dir / "src" / "test.txt").exists()

    def test_extract_wrong_password_raises(
        self, encrypted_7z_archive: Path, temp_dir: Path
    ) -> None:
        """Test that wrong passwords raise PasswordNotFoundError."""
        extractor = Extractor(encrypted_7z_archive)
        output_dir = temp_dir / "output"
        wrong_passwords = ["wrong1", "wrong2", "wrong3"]

        with pytest.raises(PasswordNotFoundError):
            extractor.extract_with_passwords(wrong_passwords, output_dir)

    def test_extract_creates_output_dir(self, plain_7z_archive: Path, temp_dir: Path) -> None:
        """Test that extraction creates output directory."""
        extractor = Extractor(plain_7z_archive)
        output_dir = temp_dir / "new_output"

        assert not output_dir.exists()
        extractor.try_extract(output_dir)
        assert output_dir.exists()

    def test_extract_plain_zip_archive(self, plain_zip_archive: Path, temp_dir: Path) -> None:
        """Test extracting a plain zip archive."""
        extractor = Extractor(plain_zip_archive)
        output_dir = temp_dir / "output"

        success, password = extractor.try_extract(output_dir)

        assert success is True
        assert password is None
        assert (output_dir / "src" / "test.txt").exists()

    def test_extract_encrypted_zip_with_password(
        self, encrypted_zip_archive: Path, temp_dir: Path
    ) -> None:
        """Test extracting encrypted zip with correct password."""
        extractor = Extractor(encrypted_zip_archive)
        output_dir = temp_dir / "output"

        success, used_password = extractor.try_extract(output_dir, ["zipsecret"])

        assert success is True
        assert used_password == "zipsecret"
        assert (output_dir / "src" / "test.txt").exists()

    @pytest.mark.parametrize(
        "passwords,expected_password",
        [
            (["secret123", "wrong1", "wrong2"], "secret123"),
            (["wrong1", "secret123", "wrong2"], "secret123"),
            (["wrong1", "wrong2", "secret123"], "secret123"),
        ],
    )
    def test_extract_encrypted_7z_password_positions(
        self,
        encrypted_7z_archive: Path,
        temp_dir: Path,
        passwords: list[str],
        expected_password: str,
    ) -> None:
        """Test extracting encrypted 7z with password at various positions."""
        extractor = Extractor(encrypted_7z_archive)
        output_dir = temp_dir / "output"

        success, used_password = extractor.try_extract(output_dir, passwords)

        assert success is True
        assert used_password == expected_password
        assert (output_dir / "src" / "test.txt").exists()

    @pytest.mark.parametrize(
        "passwords,expected_password",
        [
            (["zipsecret", "wrong1", "wrong2"], "zipsecret"),
            (["wrong1", "zipsecret", "wrong2"], "zipsecret"),
            (["wrong1", "wrong2", "zipsecret"], "zipsecret"),
        ],
    )
    def test_extract_encrypted_zip_password_positions(
        self,
        encrypted_zip_archive: Path,
        temp_dir: Path,
        passwords: list[str],
        expected_password: str,
    ) -> None:
        """Test extracting encrypted zip with password at various positions."""
        extractor = Extractor(encrypted_zip_archive)
        output_dir = temp_dir / "output"

        success, used_password = extractor.try_extract(output_dir, passwords)

        assert success is True
        assert used_password == expected_password
        assert (output_dir / "src" / "test.txt").exists()

    def test_extract_encrypted_7z_password_not_in_list(
        self, encrypted_7z_archive: Path, temp_dir: Path
    ) -> None:
        """Test extracting encrypted 7z when password is not in list."""
        extractor = Extractor(encrypted_7z_archive)
        output_dir = temp_dir / "output"
        wrong_passwords = ["wrong1", "wrong2", "wrong3"]

        success, used_password = extractor.try_extract(output_dir, wrong_passwords)

        assert success is False
        assert used_password is None

    def test_extract_encrypted_zip_password_not_in_list(
        self, encrypted_zip_archive: Path, temp_dir: Path
    ) -> None:
        """Test extracting encrypted zip when password is not in list."""
        extractor = Extractor(encrypted_zip_archive)
        output_dir = temp_dir / "output"
        wrong_passwords = ["wrong1", "wrong2", "wrong3"]

        success, used_password = extractor.try_extract(output_dir, wrong_passwords)

        assert success is False
        assert used_password is None

    def test_extract_encrypted_7z_single_correct_password(
        self, encrypted_7z_archive: Path, temp_dir: Path
    ) -> None:
        """Test extracting encrypted 7z with single correct password."""
        extractor = Extractor(encrypted_7z_archive)
        output_dir = temp_dir / "output"

        success, used_password = extractor.try_extract(output_dir, ["secret123"])

        assert success is True
        assert used_password == "secret123"
        assert (output_dir / "src" / "test.txt").exists()

    def test_extract_encrypted_7z_single_wrong_password(
        self, encrypted_7z_archive: Path, temp_dir: Path
    ) -> None:
        """Test extracting encrypted 7z with single wrong password."""
        extractor = Extractor(encrypted_7z_archive)
        output_dir = temp_dir / "output"

        success, used_password = extractor.try_extract(output_dir, ["wrongpassword"])

        assert success is False
        assert used_password is None

    def test_extract_encrypted_zip_single_wrong_password(
        self, encrypted_zip_archive: Path, temp_dir: Path
    ) -> None:
        """Test extracting encrypted zip with single wrong password."""
        extractor = Extractor(encrypted_zip_archive)
        output_dir = temp_dir / "output"

        success, used_password = extractor.try_extract(output_dir, ["wrongpassword"])

        assert success is False
        assert used_password is None

    def test_try_extract_failure_no_empty_dir(
        self, encrypted_7z_archive: Path, temp_dir: Path
    ) -> None:
        """Test that try_extract does not leave empty dir on failure."""
        extractor = Extractor(encrypted_7z_archive)
        output_dir = temp_dir / "should_not_exist"

        success, used_password = extractor.try_extract(
            output_dir, ["wrong1", "wrong2"]
        )

        assert success is False
        assert used_password is None
        assert not output_dir.exists()

    def test_extract_with_passwords_failure_no_empty_dir(
        self, encrypted_7z_archive: Path, temp_dir: Path
    ) -> None:
        """Test that extract_with_passwords does not leave empty dir on failure."""
        extractor = Extractor(encrypted_7z_archive)
        output_dir = temp_dir / "should_not_exist"

        with pytest.raises(PasswordNotFoundError):
            extractor.extract_with_passwords(["wrong1", "wrong2"], output_dir)

        assert not output_dir.exists()

    def test_try_extract_with_progress_bar(
        self, encrypted_7z_archive: Path, temp_dir: Path
    ) -> None:
        """Test extraction with progress bar enabled."""
        extractor = Extractor(encrypted_7z_archive)
        output_dir = temp_dir / "output"

        success, used_password = extractor.try_extract(
            output_dir,
            ["wrong1", "secret123"],
            show_progress=True,
            show_password_progress=True,
        )

        assert success is True
        assert used_password == "secret123"
        assert (output_dir / "src" / "test.txt").exists()

    def test_try_extract_with_progress_no_password_progress(
        self, encrypted_7z_archive: Path, temp_dir: Path
    ) -> None:
        """Test extraction with progress but no password progress."""
        extractor = Extractor(encrypted_7z_archive)
        output_dir = temp_dir / "output"

        success, used_password = extractor.try_extract(
            output_dir,
            ["secret123"],
            show_progress=True,
            show_password_progress=False,
        )

        assert success is True
        assert used_password == "secret123"
        assert (output_dir / "src" / "test.txt").exists()

    def test_extract_plain_with_progress_bar(
        self, plain_7z_archive: Path, temp_dir: Path
    ) -> None:
        """Test extracting plain archive with progress bar."""
        extractor = Extractor(plain_7z_archive)
        output_dir = temp_dir / "output"

        success, used_password = extractor.try_extract(
            output_dir,
            show_progress=True,
            show_password_progress=False,
        )

        assert success is True
        assert used_password is None
        assert (output_dir / "src" / "test.txt").exists()


class TestGet7zVersion:
    """Test cases for get_7z_version function."""

    def test_get_7z_version_unknown(self) -> None:
        """Test that get_7z_version returns 'unknown' on error."""
        with patch(
            "try7z.extractor.subprocess.run",
            side_effect=Exception("Command failed"),
        ):
            version = get_7z_version()
            assert version == "unknown"

    def test_get_7z_version_success(self) -> None:
        """Test that get_7z_version returns version string."""
        version = get_7z_version()
        assert isinstance(version, str)
        assert version != "unknown"
        assert "7-Zip" in version


class TestGet7zPath:
    """Test cases for get_7z_path function."""

    def test_get_7z_path_windows_amd64(self) -> None:
        with patch("platform.system", return_value="Windows"), patch(
            "platform.machine", return_value="AMD64"
        ):
            path = get_7z_path()
            assert path.name == "7z.exe"
            assert "win-x64" in str(path).replace("\\", "/")

    def test_get_7z_path_windows_x86_64(self) -> None:
        with patch("platform.system", return_value="Windows"), patch(
            "platform.machine", return_value="x86_64"
        ):
            path = get_7z_path()
            assert path.name == "7z.exe"

    def test_get_7z_path_linux_amd64(self) -> None:
        with patch("platform.system", return_value="Linux"), patch(
            "platform.machine", return_value="amd64"
        ):
            path = get_7z_path()
            assert path.name == "7zz"
            assert "linux-x64" in str(path).replace("\\", "/")

    def test_get_7z_path_linux_x86_64(self) -> None:
        with patch("platform.system", return_value="Linux"), patch(
            "platform.machine", return_value="x86_64"
        ):
            path = get_7z_path()
            assert path.name == "7zz"

    def test_get_7z_path_darwin(self) -> None:
        with patch("platform.system", return_value="Darwin"), patch(
            "platform.machine", return_value="x86_64"
        ):
            path = get_7z_path()
            assert path.name == "7zz"
            assert "mac-x64" in str(path).replace("\\", "/")

    def test_get_7z_path_unsupported_system(self) -> None:
        with patch("platform.system", return_value="FreeBSD"), patch(
            "platform.machine", return_value="x86_64"
        ), pytest.raises(ExtractionError, match="Unsupported platform"):
            get_7z_path()

    def test_get_7z_path_unsupported_machine(self) -> None:
        with patch("platform.system", return_value="Windows"), patch(
            "platform.machine", return_value="arm64"
        ), pytest.raises(ExtractionError, match="Unsupported platform"):
            get_7z_path()


class TestGetArchiveFileCount:
    """Test cases for _get_archive_file_count method."""

    def test_get_archive_file_count_real_archive(self, plain_7z_archive: Path) -> None:
        extractor = Extractor(plain_7z_archive)
        count = extractor._get_archive_file_count()
        # Returns int if parsing succeeds, None otherwise (depends on 7-Zip version)
        assert count is None or (isinstance(count, int) and count >= 1)

    def test_get_archive_file_count_parses_files_line(self, plain_7z_archive: Path) -> None:
        extractor = Extractor(plain_7z_archive)
        mock_output = "Files: 42\n"
        with patch(
            "try7z.extractor.subprocess.run",
            return_value=MagicMock(returncode=0, stdout=mock_output),
        ):
            count = extractor._get_archive_file_count()
            assert count == 42

    def test_get_archive_file_count_no_files_line(self, plain_7z_archive: Path) -> None:
        extractor = Extractor(plain_7z_archive)
        mock_output = "Some other output\n"
        with patch(
            "try7z.extractor.subprocess.run",
            return_value=MagicMock(returncode=0, stdout=mock_output),
        ):
            count = extractor._get_archive_file_count()
            assert count is None

    def test_get_archive_file_count_subprocess_error(self, plain_7z_archive: Path) -> None:
        extractor = Extractor(plain_7z_archive)
        with patch(
            "try7z.extractor.subprocess.run",
            side_effect=subprocess.TimeoutExpired("cmd", 60),
        ):
            count = extractor._get_archive_file_count()
            assert count is None

    def test_get_archive_file_count_nonzero_returncode(self, plain_7z_archive: Path) -> None:
        extractor = Extractor(plain_7z_archive)
        with patch(
            "try7z.extractor.subprocess.run",
            return_value=MagicMock(returncode=1, stdout=""),
        ):
            count = extractor._get_archive_file_count()
            assert count is None


class TestExtractWithProgress:
    """Test cases for _extract_with_progress method."""

    def _make_mock_process(
        self, stdout_data: bytes, stderr_data: bytes = b"", returncode: int = 0
    ) -> MagicMock:
        """Helper to create a mock subprocess.Popen for progress testing."""
        stdout_read_index = 0

        def mock_read(size: int = -1) -> bytes:
            nonlocal stdout_read_index
            if stdout_read_index >= len(stdout_data):
                return b""
            byte = stdout_data[stdout_read_index : stdout_read_index + 1]
            stdout_read_index += 1
            return byte

        mock_stdout = MagicMock()
        mock_stdout.read.side_effect = mock_read

        mock_process = MagicMock()
        mock_process.stdout = mock_stdout
        mock_process.returncode = returncode

        return mock_process

    def test_extract_with_progress_success(self, plain_7z_archive: Path, temp_dir: Path) -> None:
        extractor = Extractor(plain_7z_archive)
        output_dir = temp_dir / "output"

        stdout_data = b" 10%\r 50%\r100%\r\n"
        mock_process = self._make_mock_process(stdout_data, returncode=0)

        with patch("subprocess.Popen", return_value=mock_process), patch.object(
            mock_process, "communicate", return_value=(b"", b"")
        ), patch("tqdm.tqdm"):
            result = extractor._extract_with_progress(
                [
                    str(extractor._7z_path),
                    "x",
                    "-y",
                    f"-o{output_dir}",
                    str(plain_7z_archive),
                ]
            )
            assert result is True

    def test_extract_with_progress_wrong_password(
        self, encrypted_7z_archive: Path, temp_dir: Path
    ) -> None:
        extractor = Extractor(encrypted_7z_archive)
        output_dir = temp_dir / "output"

        stdout_data = b"wrong password\r\n"
        mock_process = self._make_mock_process(stdout_data, returncode=2)

        with patch("subprocess.Popen", return_value=mock_process), patch.object(
            mock_process, "communicate", return_value=(b"", b"Wrong password")
        ), patch("tqdm.tqdm"):
            result = extractor._extract_with_progress(
                [
                    str(extractor._7z_path),
                    "x",
                    "-y",
                    f"-o{output_dir}",
                    str(encrypted_7z_archive),
                ]
            )
            assert result is False

    def test_extract_with_progress_extraction_error(
        self, plain_7z_archive: Path, temp_dir: Path
    ) -> None:
        extractor = Extractor(plain_7z_archive)
        output_dir = temp_dir / "output"

        stdout_data = b"some error output\n"
        mock_process = self._make_mock_process(stdout_data, returncode=1)

        with patch("subprocess.Popen", return_value=mock_process), patch.object(
            mock_process, "communicate", return_value=(b"", b"Fatal error")
        ), patch("tqdm.tqdm"), pytest.raises(ExtractionError, match="Extraction failed"):
            extractor._extract_with_progress(
                [
                    str(extractor._7z_path),
                    "x",
                    "-y",
                    f"-o{output_dir}",
                    str(plain_7z_archive),
                ]
            )


class TestTryPasswords:
    """Test cases for _try_passwords helper method."""

    def test_try_passwords_first_success(self, plain_7z_archive: Path, temp_dir: Path) -> None:
        """Test that _try_passwords succeeds on first password."""
        extractor = Extractor(plain_7z_archive)
        output_dir = temp_dir / "output"

        success, password, attempts = extractor._try_passwords(output_dir, [None])

        assert success is True
        assert password is None
        assert attempts == 1

    def test_try_passwords_success_on_second(
        self, encrypted_7z_archive: Path, temp_dir: Path
    ) -> None:
        """Test that _try_passwords succeeds on second password."""
        extractor = Extractor(encrypted_7z_archive)
        output_dir = temp_dir / "output"

        success, password, attempts = extractor._try_passwords(
            output_dir, ["wrong", "secret123"]
        )

        assert success is True
        assert password == "secret123"
        assert attempts == 2

    def test_try_passwords_all_fail(self, encrypted_7z_archive: Path, temp_dir: Path) -> None:
        """Test that _try_passwords returns failure when no password works."""
        extractor = Extractor(encrypted_7z_archive)
        output_dir = temp_dir / "output"

        success, password, attempts = extractor._try_passwords(
            output_dir, ["wrong1", "wrong2"]
        )

        assert success is False
        assert password is None
        assert attempts == 2

    def test_try_passwords_shows_progress(
        self, encrypted_7z_archive: Path, temp_dir: Path, capsys
    ) -> None:
        """Test that _try_passwords shows progress when enabled."""
        extractor = Extractor(encrypted_7z_archive)
        output_dir = temp_dir / "output"

        extractor._try_passwords(
            output_dir, ["wrong", "secret123"], show_password_progress=True
        )

        captured = capsys.readouterr()
        assert "Trying password" in captured.out

    def test_try_passwords_propagates_extraction_error(
        self, plain_7z_archive: Path, temp_dir: Path
    ) -> None:
        """Test that _try_passwords propagates ExtractionError."""
        extractor = Extractor(plain_7z_archive)
        output_dir = temp_dir / "output"

        with patch.object(
            extractor,
            "_extract_with_password",
            side_effect=ExtractionError("Corrupted archive"),
        ), pytest.raises(ExtractionError, match="Corrupted archive"):
            extractor._try_passwords(output_dir, [None])

    def test_try_passwords_catches_non_extraction_exceptions(
        self, plain_7z_archive: Path, temp_dir: Path
    ) -> None:
        """Test that _try_passwords catches non-ExtractionError exceptions and continues."""
        extractor = Extractor(plain_7z_archive)
        output_dir = temp_dir / "output"

        call_count = 0

        def mock_extract(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Unexpected error")
            return True

        with patch.object(extractor, "_extract_with_password", side_effect=mock_extract):
            success, password, attempts = extractor._try_passwords(
                output_dir, ["pwd1", "pwd2"]
            )

        assert success is True
        assert password == "pwd2"
        assert attempts == 2
        assert call_count == 2


class TestComputeSkipDepth:
    """Tests for _compute_skip_depth."""

    def test_empty_dir(self, temp_dir: Path) -> None:
        """Empty temp dir returns 0."""
        assert _compute_skip_depth(temp_dir) == 0

    def test_multiple_root_entries(self, temp_dir: Path) -> None:
        """Multiple entries at root returns 0."""
        (temp_dir / "file1.txt").write_text("")
        (temp_dir / "dir1").mkdir()
        assert _compute_skip_depth(temp_dir) == 0

    def test_single_root_file(self, temp_dir: Path) -> None:
        """Single file at root returns 0."""
        (temp_dir / "readme.txt").write_text("")
        assert _compute_skip_depth(temp_dir) == 0

    def test_single_child_dir(self, temp_dir: Path) -> None:
        """Single orphan subdir returns 1."""
        root = temp_dir / "A"
        root.mkdir()
        orphan = root / "B"
        orphan.mkdir()
        (orphan / "C1").mkdir()
        (orphan / "C2").mkdir()
        assert _compute_skip_depth(temp_dir) == 1

    def test_deep_chain(self, temp_dir: Path) -> None:
        """Deep single-child chain returns correct depth."""
        chain = temp_dir / "A" / "B" / "C" / "D"
        chain.mkdir(parents=True)
        (chain / "file.txt").write_text("")
        assert _compute_skip_depth(temp_dir) == 3

    def test_multiple_dirs_at_second_level(self, temp_dir: Path) -> None:
        """Root with multiple subdirs returns 0."""
        root = temp_dir / "A"
        root.mkdir()
        (root / "src").mkdir()
        (root / "doc").mkdir()
        assert _compute_skip_depth(temp_dir) == 0

    def test_mixed_file_and_dir_at_second_level(self, temp_dir: Path) -> None:
        """Root with file + dir returns 0."""
        root = temp_dir / "A"
        root.mkdir()
        (root / "readme.txt").write_text("")
        (root / "src").mkdir()
        (root / "src" / "main.py").write_text("")
        assert _compute_skip_depth(temp_dir) == 0

    def test_no_common_root(self, temp_dir: Path) -> None:
        """No single root entry returns 0."""
        (temp_dir / "file.txt").write_text("")
        (temp_dir / "dir").mkdir()
        assert _compute_skip_depth(temp_dir) == 0


class TestFlattenAndMove:
    """Tests for _flatten_and_move."""

    def test_no_flattening_single_root(self, temp_dir: Path) -> None:
        """skip_depth=0 moves root contents to output."""
        src = temp_dir / "src"
        src.mkdir()
        root = src / "MyApp"
        root.mkdir()
        (root / "main.py").write_text("code")
        (root / "doc").mkdir()
        (root / "doc" / "readme.txt").write_text("docs")

        output = temp_dir / "out"

        _flatten_and_move(src, output, skip_depth=0)

        assert output.is_dir()
        assert (output / "MyApp" / "main.py").exists()
        assert (output / "MyApp" / "doc" / "readme.txt").exists()

    def test_flatten_single_level(self, temp_dir: Path) -> None:
        """skip_depth=1 moves orphan's children up to root."""
        src = temp_dir / "src"
        src.mkdir()
        root = src / "MyProject"
        root.mkdir()
        orphan = root / "src"
        orphan.mkdir()
        (orphan / "main.py").write_text("code")
        (orphan / "utils.py").write_text("helpers")

        output = temp_dir / "out"

        _flatten_and_move(src, output, skip_depth=1)

        assert output.is_dir()
        assert (output / "MyProject" / "main.py").exists()
        assert (output / "MyProject" / "utils.py").exists()
        assert not (output / "MyProject" / "src").exists()

    def test_flatten_deep_chain(self, temp_dir: Path) -> None:
        """skip_depth=3 flattens deep single-child chain."""
        src = temp_dir / "src"
        src.mkdir()
        root = src / "A"
        root.mkdir()
        chain = root / "B" / "C" / "D"
        chain.mkdir(parents=True)
        (chain / "file.txt").write_text("deep")

        output = temp_dir / "out"

        _flatten_and_move(src, output, skip_depth=3)

        assert output.is_dir()
        assert (output / "A" / "file.txt").exists()
        assert not (output / "A" / "B").exists()

    def test_empty_temp_dir(self, temp_dir: Path) -> None:
        """Empty temp dir creates empty output dir."""
        src = temp_dir / "src"
        src.mkdir()
        output = temp_dir / "out"

        _flatten_and_move(src, output, skip_depth=0)

        assert output.is_dir()

    def test_flatten_preserves_sibling_dirs(self, temp_dir: Path) -> None:
        """Multiple dirs under orphan are moved together."""
        src = temp_dir / "src"
        src.mkdir()
        root = src / "App"
        root.mkdir()
        orphan = root / "lib"
        orphan.mkdir()
        (orphan / "foo").mkdir()
        (orphan / "bar").mkdir()
        (orphan / "foo" / "f.py").write_text("f")
        (orphan / "bar" / "b.py").write_text("b")

        output = temp_dir / "out"

        _flatten_and_move(src, output, skip_depth=1)

        assert output.is_dir()
        assert (output / "App" / "foo" / "f.py").exists()
        assert (output / "App" / "bar" / "b.py").exists()
        assert not (output / "App" / "lib").exists()

    def test_single_root_file(self, temp_dir: Path) -> None:
        """temp_dir contains a single file, skip_depth=0 -> file moved to output."""
        src = temp_dir / "src"
        src.mkdir()
        (src / "README.md").write_text("hello world")

        output = temp_dir / "out"

        _flatten_and_move(src, output, skip_depth=0)

        assert output.is_dir()
        assert (output / "README.md").exists()
        assert not (output / "README.md").is_dir()
        assert (output / "README.md").read_text() == "hello world"

    def test_skip_depth_too_large(self, temp_dir: Path) -> None:
        """skip_depth > actual chain depth doesn't crash; treats leaf as stopping point."""
        src = temp_dir / "src"
        src.mkdir()
        root = src / "A"
        root.mkdir()
        (root / "file.txt").write_text("content")

        output = temp_dir / "out"

        _flatten_and_move(src, output, skip_depth=5)

        assert output.is_dir()
        assert (output / "A" / "file.txt").exists()
        assert (output / "A" / "file.txt").read_text() == "content"
