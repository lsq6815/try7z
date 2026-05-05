"""Tests for Extractor."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from try7z.extractor import Extractor, get_7z_path, get_7z_version
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
        with patch("platform.system", return_value="Windows"):
            with patch("platform.machine", return_value="AMD64"):
                path = get_7z_path()
                assert path.name == "7z.exe"
                assert "win-x64" in str(path).replace("\\", "/")

    def test_get_7z_path_windows_x86_64(self) -> None:
        with patch("platform.system", return_value="Windows"):
            with patch("platform.machine", return_value="x86_64"):
                path = get_7z_path()
                assert path.name == "7z.exe"

    def test_get_7z_path_linux_amd64(self) -> None:
        with patch("platform.system", return_value="Linux"):
            with patch("platform.machine", return_value="amd64"):
                path = get_7z_path()
                assert path.name == "7zz"
                assert "linux-x64" in str(path).replace("\\", "/")

    def test_get_7z_path_linux_x86_64(self) -> None:
        with patch("platform.system", return_value="Linux"):
            with patch("platform.machine", return_value="x86_64"):
                path = get_7z_path()
                assert path.name == "7zz"

    def test_get_7z_path_darwin(self) -> None:
        with patch("platform.system", return_value="Darwin"):
            with patch("platform.machine", return_value="x86_64"):
                path = get_7z_path()
                assert path.name == "7zz"
                assert "mac-x64" in str(path).replace("\\", "/")

    def test_get_7z_path_unsupported_system(self) -> None:
        with patch("platform.system", return_value="FreeBSD"):
            with patch("platform.machine", return_value="x86_64"):
                with pytest.raises(ExtractionError, match="Unsupported platform"):
                    get_7z_path()

    def test_get_7z_path_unsupported_machine(self) -> None:
        with patch("platform.system", return_value="Windows"):
            with patch("platform.machine", return_value="arm64"):
                with pytest.raises(ExtractionError, match="Unsupported platform"):
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

        with patch("subprocess.Popen", return_value=mock_process):
            with patch.object(mock_process, "communicate", return_value=(b"", b"")):
                with patch("tqdm.tqdm"):
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

        with patch("subprocess.Popen", return_value=mock_process):
            with patch.object(
                mock_process, "communicate", return_value=(b"", b"Wrong password")
            ):
                with patch("tqdm.tqdm"):
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

        with patch("subprocess.Popen", return_value=mock_process):
            with patch.object(
                mock_process, "communicate", return_value=(b"", b"Fatal error")
            ):
                with patch("tqdm.tqdm"):
                    with pytest.raises(ExtractionError, match="Extraction failed"):
                        extractor._extract_with_progress(
                            [
                                str(extractor._7z_path),
                                "x",
                                "-y",
                                f"-o{output_dir}",
                                str(plain_7z_archive),
                            ]
                        )
