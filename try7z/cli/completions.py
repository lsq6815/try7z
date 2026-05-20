"""Shell completion script generation and installation for try7z.

This module generates bash and PowerShell completion scripts for the try7z
CLI and provides installation helpers.

Usage:
    Direct stdout (user pipes or redirects)::

        $ try7z autocompletion --shell bash > /tmp/try7z-completion.bash
        $ source /tmp/try7z-completion.bash

    Automatic install::

        $ try7z autocompletion --shell bash --install
        $ try7z autocompletion --shell pwsh --install
        $ try7z autocompletion --shell powershell --install
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def generate_bash_completion() -> str:
    """Generate bash completion script for try7z.

    Returns:
        Bash completion script as a string.

    Example:
        >>> script = generate_bash_completion()
        >>> "_try7z_completion" in script
        True
        >>> "add" in script
        True
    """
    return r"""# try7z bash completion script
# Generated automatically - do not edit manually

_try7z_completion() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    local commands="add remove list clear path edit extract autocompletion"
    local global_opts="-h --help -v --version"

    # If we are completing the first argument (command)
    if [ ${COMP_CWORD} -eq 1 ]; then
        COMPREPLY=( $(compgen -W "${commands} ${global_opts}" -- "${cur}") )
        return 0
    fi

    local cmd="${COMP_WORDS[1]}"

    case "${cmd}" in
        add)
            COMPREPLY=( $(compgen -W "-h --help" -- "${cur}") )
            ;;
        remove)
            if [ "${prev}" = "-i" ] || [ "${prev}" = "--index" ]; then
                COMPREPLY=()
            else
                COMPREPLY=( $(compgen -W "-i --index -h --help" -- "${cur}") )
            fi
            ;;
        list|path|edit)
            COMPREPLY=( $(compgen -W "-h --help" -- "${cur}") )
            ;;
        clear)
            COMPREPLY=( $(compgen -W "-f --force -h --help" -- "${cur}") )
            ;;
        extract)
            case "${prev}" in
                -o|--output)
                    COMPREPLY=( $(compgen -d -- "${cur}") )
                    ;;
                -p|--password)
                    COMPREPLY=()
                    ;;
                *)
                    if [[ "${cur}" == -* ]]; then
                        COMPREPLY=( $(compgen -W \
                            "-o --output -p --password -f --force -h --help" \
                            -- "${cur}") )
                    else
                        COMPREPLY=( $(compgen -f -X '!*.7z !*.zip !*.rar' \
                            -- "${cur}") )
                    fi
                    ;;
            esac
            ;;
        autocompletion)
            case "${prev}" in
                --shell)
                    COMPREPLY=( $(compgen -W "bash pwsh powershell" -- "${cur}") )
                    ;;
                *)
                    COMPREPLY=( $(compgen -W "--shell --install -h --help" \
                        -- "${cur}") )
                    ;;
            esac
            ;;
        *)
            COMPREPLY=( $(compgen -W "${global_opts}" -- "${cur}") )
            ;;
    esac
}

complete -F _try7z_completion try7z
"""


def _get_pwsh_completion_script(shell_type: str) -> str:
    """Generate PowerShell completion script content.

    Args:
        shell_type: Either "pwsh" or "powershell" for header comment.

    Returns:
        PowerShell completion script as a string.
    """
    return f"""# try7z {shell_type} completion script
# Generated automatically - do not edit manually

Register-ArgumentCompleter -Native -CommandName try7z -ScriptBlock {{
    param($wordToComplete, $commandAst, $cursorPosition)

    $commands = @('add', 'remove', 'list', 'clear', 'path', 'edit',
        'extract', 'autocompletion')
    $globalOpts = @('-h', '--help', '-v', '--version')

    $tokens = $commandAst.CommandElements |
        ForEach-Object {{ $_.Value }}
    $cmd = $tokens[1]

    # Complete first argument (command) or global options
    if ($tokens.Count -eq 1 -or
        ($tokens.Count -eq 2 -and $wordToComplete -ne '')) {{
        $commands + $globalOpts |
            Where-Object {{ $_ -like "$wordToComplete*" }} |
            ForEach-Object {{
                [System.Management.Automation.CompletionResult]::new(
                    $_, $_, 'ParameterValue', $_)
            }}
        return
    }}

    switch ($cmd) {{
        'add' {{
            @('-h', '--help') |
                Where-Object {{ $_ -like "$wordToComplete*" }} |
                ForEach-Object {{
                    [System.Management.Automation.CompletionResult]::new(
                        $_, $_, 'ParameterValue', $_)
                }}
        }}
        'remove' {{
            if ($tokens[-2] -eq '-i' -or
                $tokens[-2] -eq '--index') {{
                return
            }}
            @('-i', '--index', '-h', '--help') |
                Where-Object {{ $_ -like "$wordToComplete*" }} |
                ForEach-Object {{
                    [System.Management.Automation.CompletionResult]::new(
                        $_, $_, 'ParameterValue', $_)
                }}
        }}
        'list' {{
            @('-h', '--help') |
                Where-Object {{ $_ -like "$wordToComplete*" }} |
                ForEach-Object {{
                    [System.Management.Automation.CompletionResult]::new(
                        $_, $_, 'ParameterValue', $_)
                }}
        }}
        'path' {{
            @('-h', '--help') |
                Where-Object {{ $_ -like "$wordToComplete*" }} |
                ForEach-Object {{
                    [System.Management.Automation.CompletionResult]::new(
                        $_, $_, 'ParameterValue', $_)
                }}
        }}
        'edit' {{
            @('-h', '--help') |
                Where-Object {{ $_ -like "$wordToComplete*" }} |
                ForEach-Object {{
                    [System.Management.Automation.CompletionResult]::new(
                        $_, $_, 'ParameterValue', $_)
                }}
        }}
        'clear' {{
            @('-f', '--force', '-h', '--help') |
                Where-Object {{ $_ -like "$wordToComplete*" }} |
                ForEach-Object {{
                    [System.Management.Automation.CompletionResult]::new(
                        $_, $_, 'ParameterValue', $_)
                }}
        }}
        'extract' {{
            $prev = $tokens[-2]
            if ($prev -eq '-o' -or $prev -eq '--output') {{
                Get-ChildItem -Directory -Name "$wordToComplete*" |
                    ForEach-Object {{
                        $ct = $_
                        if ($ct -match ' ') {{ $ct = '"{{0}}"' -f $ct }}
                        [System.Management.Automation.CompletionResult]::new(
                            $ct, $_, 'ProviderItem', $_)
                    }}
                return
            }}
            if ($prev -eq '-p' -or $prev -eq '--password') {{
                return
            }}
            if ($wordToComplete -like '-*') {{
                @('-o', '--output', '-p', '--password',
                    '-f', '--force', '-h', '--help') |
                    Where-Object {{ $_ -like "$wordToComplete*" }} |
                    ForEach-Object {{
                        [System.Management.Automation.CompletionResult]::new(
                            $_, $_, 'ParameterValue', $_)
                    }}
            }} else {{
                Get-ChildItem -Name "$wordToComplete*" |
                    Where-Object {{ $_ -match '\\.(7z|zip|rar)$' }} |
                    ForEach-Object {{
                        $ct = $_
                        if ($ct -match ' ') {{ $ct = '"{{0}}"' -f $ct }}
                        [System.Management.Automation.CompletionResult]::new(
                            $ct, $_, 'ProviderItem', $_)
                    }}
            }}
        }}
        'autocompletion' {{
            $prev = $tokens[-2]
            if ($prev -eq '--shell') {{
                @('bash', 'pwsh', 'powershell') |
                    Where-Object {{ $_ -like "$wordToComplete*" }} |
                    ForEach-Object {{
                        [System.Management.Automation.CompletionResult]::new(
                            $_, $_, 'ParameterValue', $_)
                    }}
                return
            }}
            @('--shell', '--install', '-h', '--help') |
                Where-Object {{ $_ -like "$wordToComplete*" }} |
                ForEach-Object {{
                    [System.Management.Automation.CompletionResult]::new(
                        $_, $_, 'ParameterValue', $_)
                }}
        }}
        default {{
            $globalOpts |
                Where-Object {{ $_ -like "$wordToComplete*" }} |
                ForEach-Object {{
                    [System.Management.Automation.CompletionResult]::new(
                        $_, $_, 'ParameterValue', $_)
                }}
        }}
    }}
}}
"""


def generate_pwsh_completion() -> str:
    """Generate pwsh (PowerShell Core 7+) completion script.

    Returns:
        PowerShell completion script as a string.

    Example:
        >>> script = generate_pwsh_completion()
        >>> "Register-ArgumentCompleter" in script
        True
        >>> "try7z pwsh completion script" in script
        True
    """
    return _get_pwsh_completion_script("pwsh")


def generate_powershell_completion() -> str:
    """Generate PowerShell (Windows PowerShell 5.1) completion script.

    Returns:
        PowerShell completion script as a string.

    Example:
        >>> script = generate_powershell_completion()
        >>> "Register-ArgumentCompleter" in script
        True
        >>> "try7z powershell completion script" in script
        True
    """
    return _get_pwsh_completion_script("powershell")


def _get_bashrc_path() -> Path:
    """Get path to bashrc file.

    Returns:
        Path to ~/.bashrc.
    """
    return Path.home() / ".bashrc"


def _get_pwsh_profile_path() -> Path:
    """Get path to PowerShell Core (pwsh) profile.

    Returns:
        Path to pwsh profile file.

    Raises:
        ValueError: On Linux/macOS where pwsh is not supported.
    """
    if sys.platform == "win32":
        # Try to get profile path via pwsh command
        try:
            result = subprocess.run(
                ["pwsh", "-NoProfile", "-Command", "$PROFILE"],
                capture_output=True,
                text=True,
                check=True,
            )
            profile_path = result.stdout.strip()
            if profile_path:
                return Path(profile_path)
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        # Fallback for Windows
        docs = Path.home() / "Documents"
        if not docs.exists():
            docs = Path.home() / "My Documents"
        return docs / "PowerShell" / "Microsoft.PowerShell_profile.ps1"
    else:
        # Linux/macOS: pwsh is not supported
        raise ValueError("PowerShell Core (pwsh) completion is not supported on Linux/macOS.")


def _get_powershell_profile_path() -> Path:
    """Get path to Windows PowerShell (powershell.exe) profile.

    Returns:
        Path to Windows PowerShell profile file.

    Raises:
        ValueError: On Linux/macOS where Windows PowerShell is not supported.
    """
    if sys.platform == "win32":
        # Try to get profile path via powershell command
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "$PROFILE"],
                capture_output=True,
                text=True,
                check=True,
            )
            profile_path = result.stdout.strip()
            if profile_path:
                return Path(profile_path)
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        # Fallback for Windows
        docs = Path.home() / "Documents"
        if not docs.exists():
            docs = Path.home() / "My Documents"
        return docs / "WindowsPowerShell" / "Microsoft.PowerShell_profile.ps1"
    else:
        # Linux/macOS: Windows PowerShell is not supported
        raise ValueError("Windows PowerShell is not supported on Linux/macOS.")


def install_bash_completion() -> None:
    """Install bash completion script.

    Writes the completion script to ~/.try7z-completion.bash and
    adds a source line to ~/.bashrc if not already present.

    Raises:
        OSError: If writing files fails.
    """
    completion_file = Path.home() / ".try7z-completion.bash"
    completion_script = generate_bash_completion()

    completion_file.write_text(completion_script, encoding="utf-8")

    bashrc = _get_bashrc_path()
    source_line = f'[ -f "{completion_file}" ] && source "{completion_file}"'

    if bashrc.exists():
        content = bashrc.read_text(encoding="utf-8")
        if source_line not in content:
            with bashrc.open("a", encoding="utf-8") as f:
                f.write(f"\n# try7z shell completion\n{source_line}\n")
    else:
        bashrc.write_text(
            f"# try7z shell completion\n{source_line}\n",
            encoding="utf-8",
        )


def _install_pwsh_completion_common(profile: Path, script: str) -> None:
    """Common logic for installing PowerShell completion script.

    Args:
        profile: Path to the PowerShell profile file.
        script: The completion script content to install.

    Raises:
        OSError: If writing files fails.
    """
    # Ensure parent directory exists
    profile.parent.mkdir(parents=True, exist_ok=True)

    if profile.exists():
        content = profile.read_text(encoding="utf-8")
        # Avoid duplicating the completion script
        marker = "try7z pwsh completion script"
        if marker not in content:
            marker = "try7z powershell completion script"

        if marker in content:
            # Replace existing script block by finding it
            lines = content.splitlines(keepends=True)
            new_lines: list[str] = []
            skip = False
            brace_count = 0
            seen_brace = False
            for line in lines:
                if marker in line:
                    skip = True
                    brace_count = 0
                    seen_brace = False
                    continue
                if skip:
                    brace_count += line.count("{")
                    brace_count -= line.count("}")
                    if "{" in line:
                        seen_brace = True
                    if seen_brace and brace_count == 0:
                        skip = False
                    continue
                new_lines.append(line)
            # Append new script
            if new_lines and not new_lines[-1].endswith("\n"):
                new_lines.append("\n")
            new_lines.append("\n" + script + "\n")
            profile.write_text("".join(new_lines), encoding="utf-8")
        else:
            with profile.open("a", encoding="utf-8") as f:
                f.write("\n" + script + "\n")
    else:
        profile.write_text(script + "\n", encoding="utf-8")


def install_pwsh_completion() -> None:
    """Install PowerShell Core (pwsh) completion script.

    Appends the completion script to the PowerShell Core profile file.
    Creates the profile directory if it does not exist.

    Raises:
        OSError: If writing files fails.
        ValueError: On Linux/macOS where pwsh is not supported.
    """
    profile = _get_pwsh_profile_path()
    completion_script = generate_pwsh_completion()
    _install_pwsh_completion_common(profile, completion_script)


def install_powershell_completion() -> None:
    """Install Windows PowerShell (powershell.exe) completion script.

    Appends the completion script to the Windows PowerShell profile file.
    Creates the profile directory if it does not exist.

    Raises:
        OSError: If writing files fails.
        ValueError: On Linux/macOS where Windows PowerShell is not supported.
    """
    profile = _get_powershell_profile_path()
    completion_script = generate_powershell_completion()
    _install_pwsh_completion_common(profile, completion_script)


def install_completion(shell: str) -> None:
    """Install completion script for the specified shell.

    Args:
        shell: Shell type, one of "bash", "pwsh", or "powershell".

    Raises:
        ValueError: If shell type is not supported.

    Example:
        >>> install_completion("bash")
        # Installs bash completion to ~/.try7z-completion.bash
    """
    if shell == "bash":
        install_bash_completion()
    elif shell == "pwsh":
        install_pwsh_completion()
    elif shell == "powershell":
        install_powershell_completion()
    else:
        raise ValueError(
            f"Unsupported shell: {shell}. Use 'bash', 'pwsh', or 'powershell'."
        )
