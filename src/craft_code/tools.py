import os
import re
import subprocess
import fnmatch
from pathlib import Path
from typing import Dict, List, Tuple
from craft_code.utils import safe_path, BASE_DIR

# ============================================================================
# Tool Definitions (OpenAI Function Calling Format)
# ============================================================================

tools = [
    # ========== Core Tools ==========
    {
        "type": "function",
        "function": {
            "name": "read",
            "description": "Read file contents. Text files limited to 20KB. Returns first 2000 lines by default, with lines truncated at 2000 chars. Use offset/limit for large files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to file (relative to workspace)",
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Line number to start from (0-indexed, optional)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of lines to read (optional, default: 2000)",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write",
            "description": "Write or overwrite file contents. Creates parent directories automatically.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to file (relative to workspace)",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit",
            "description": "Replace exact text in file. Must match exactly including whitespace. Fails if text not found or appears multiple times. For precise edits, read the file first to get exact text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to file (relative to workspace)",
                    },
                    "old_text": {
                        "type": "string",
                        "description": "Exact text to find (must match exactly)",
                    },
                    "new_text": {
                        "type": "string",
                        "description": "Text to replace with",
                    },
                },
                "required": ["path", "old_text", "new_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Execute shell command in workspace directory. Use for git operations, running tests, building, installing packages, etc. Commands run with 120s timeout (max 600s). Potentially dangerous commands require user approval.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (optional, default: 120, max: 600)",
                    },
                },
                "required": ["command"],
            },
        },
    },
    # ========== Read-Only Tools ==========
    {
        "type": "function",
        "function": {
            "name": "grep",
            "description": "Search for text or regex pattern in files. Returns matching lines with line numbers. Searches recursively from specified path. Respects .gitignore.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Text or regex pattern to search for",
                    },
                    "path": {
                        "type": "string",
                        "description": "File or directory to search (optional, default: '.')",
                    },
                    "case_sensitive": {
                        "type": "boolean",
                        "description": "Case sensitive search (optional, default: false)",
                    },
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find",
            "description": "Find files matching glob pattern. Respects .gitignore. Examples: '*.py', 'src/**/*.js', '**/*.md'",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern to match files",
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory to search (optional, default: '.')",
                    },
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ls",
            "description": "List directory contents including files and subdirectories. Shows hidden files by default.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path (optional, default: '.')",
                    },
                },
                "required": [],
            },
        },
    },
]


# ============================================================================
# Security: Dangerous Command Detection
# ============================================================================

DANGEROUS_PATTERNS = [
    (r'rm\s+-rf\s+/', "Recursive force delete of root paths"),
    (r'sudo\s+', "Requires elevated privileges"),
    (r'curl\s+.*\|\s*(sh|bash)', "Executes remote script directly"),
    (r'wget\s+.*\|\s*(sh|bash)', "Executes remote script directly"),
    (r'dd\s+if=', "Direct disk operation"),
    (r'mkfs', "Filesystem creation"),
    (r':\(\)\{.*:\|:.*\};:', "Fork bomb pattern"),
    (r'chmod\s+777', "Overly permissive file permissions"),
    (r'>\s*/dev/sd[a-z]', "Writing directly to disk device"),
]


def is_dangerous_command(command: str) -> Tuple[bool, str]:
    """Check if command matches dangerous patterns.

    Args:
        command: Shell command to check

    Returns:
        Tuple of (is_dangerous, reason)
    """
    # Check predefined patterns
    for pattern, reason in DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return True, reason

    # Check for absolute paths outside workspace
    # Match paths like /etc/passwd, /tmp/file, etc.
    abs_path_pattern = r'(?:^|\s)(/[^\s]+)'
    matches = re.findall(abs_path_pattern, command)

    for path in matches:
        # Skip common safe paths
        if path.startswith(('/bin/', '/usr/bin/', '/usr/local/bin/')):
            continue

        # Check if path is outside workspace
        real_path = os.path.realpath(path) if os.path.exists(path) else path
        if not real_path.startswith(BASE_DIR):
            return True, f"References path outside workspace: {path}"

    return False, ""


# ============================================================================
# Tool Implementations
# ============================================================================


def read(path: str, offset: int = 0, limit: int = 2000) -> Dict:
    """Read file contents with pagination support.

    Args:
        path: Path to file
        offset: Line number to start from (0-indexed)
        limit: Number of lines to read

    Returns:
        Dict with content or error
    """
    try:
        safe_file = safe_path(path)

        if not os.path.isfile(safe_file):
            return {"error": f"{path} is not a file"}

        # Check file size limit (20KB)
        max_size = 20 * 1024
        size = os.path.getsize(safe_file)
        if size > max_size:
            return {
                "error": f"File too large ({size} bytes, max {max_size} bytes). Use offset/limit parameters to read in chunks."
            }

        # Read file
        with open(safe_file, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        total_lines = len(lines)

        # Apply offset and limit
        end = min(offset + limit, total_lines)
        selected_lines = lines[offset:end]

        # Truncate long lines at 2000 chars
        truncated_lines = []
        for line in selected_lines:
            if len(line) > 2000:
                truncated_lines.append(line[:2000] + "... [truncated]\n")
            else:
                truncated_lines.append(line)

        content = "".join(truncated_lines)

        return {
            "content": content,
            "total_lines": total_lines,
            "lines_read": len(selected_lines),
            "offset": offset,
        }

    except Exception as e:
        return {"error": str(e)}


def write(path: str, content: str) -> Dict:
    """Write or overwrite file contents.

    Args:
        path: Path to file
        content: Content to write

    Returns:
        Dict with success status or error
    """
    try:
        safe_file = safe_path(path)

        # Create parent directories
        os.makedirs(os.path.dirname(safe_file) or ".", exist_ok=True)

        # Write file
        with open(safe_file, "w", encoding="utf-8") as f:
            f.write(content)

        return {
            "success": True,
            "message": f"Wrote {len(content)} bytes to {path}",
        }

    except Exception as e:
        return {"error": str(e)}


def edit(path: str, old_text: str, new_text: str) -> Dict:
    """Replace exact text in file.

    Args:
        path: Path to file
        old_text: Exact text to find
        new_text: Text to replace with

    Returns:
        Dict with success status or error
    """
    try:
        safe_file = safe_path(path)

        if not os.path.isfile(safe_file):
            return {"error": f"{path} is not a file"}

        # Read file
        with open(safe_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Count occurrences
        count = content.count(old_text)

        if count == 0:
            return {"error": f"Text not found in {path}"}

        if count > 1:
            return {
                "error": f"Text appears {count} times in {path}. Edit must match exactly once. Use read to find unique text."
            }

        # Replace (exactly once)
        new_content = content.replace(old_text, new_text, 1)

        # Write back
        with open(safe_file, "w", encoding="utf-8") as f:
            f.write(new_content)

        return {
            "success": True,
            "message": f"Replaced text in {path}",
            "replacements": 1,
        }

    except Exception as e:
        return {"error": str(e)}


def bash(command: str, timeout: int = 120) -> Dict:
    """Execute shell command with safety checks.

    Args:
        command: Shell command to execute
        timeout: Timeout in seconds (max 600)

    Returns:
        Dict with stdout/stderr or error/warning
    """
    try:
        # Cap timeout at 10 minutes
        timeout = min(timeout, 600)

        # Execute command
        result = subprocess.run(
            command,
            shell=True,
            cwd=BASE_DIR,  # Run in workspace directory
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,  # No interactive input
        )

        # Truncate output at 100KB
        max_output = 100 * 1024
        stdout = result.stdout[:max_output] if result.stdout else ""
        stderr = result.stderr[:max_output] if result.stderr else ""

        if len(result.stdout or "") > max_output:
            stdout += "\n... [output truncated at 100KB]"
        if len(result.stderr or "") > max_output:
            stderr += "\n... [output truncated at 100KB]"

        return {
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": result.returncode,
            "command": command,
        }

    except subprocess.TimeoutExpired:
        return {
            "error": f"Command timed out after {timeout}s",
            "command": command,
            "exit_code": -1,
        }
    except Exception as e:
        return {"error": str(e), "command": command}


def grep(pattern: str, path: str = ".", case_sensitive: bool = False) -> Dict:
    """Search for pattern in files.

    Args:
        pattern: Text or regex pattern to search
        path: File or directory to search
        case_sensitive: Case sensitive search

    Returns:
        Dict with matches or error
    """
    try:
        safe_search_path = safe_path(path)

        # Compile regex
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            regex = re.compile(pattern, flags)
        except re.error as e:
            return {"error": f"Invalid regex pattern: {e}"}

        matches = []

        # Gitignore patterns to skip
        ignore_dirs = {
            ".git",
            "node_modules",
            "__pycache__",
            ".venv",
            "venv",
            "build",
            "dist",
            ".pytest_cache",
            ".mypy_cache",
        }

        # Search in file
        if os.path.isfile(safe_search_path):
            with open(safe_search_path, "r", encoding="utf-8", errors="ignore") as f:
                for line_num, line in enumerate(f, start=1):
                    if regex.search(line):
                        matches.append(
                            {
                                "file": path,
                                "line": line_num,
                                "text": line.rstrip()[:500],  # Truncate long lines
                            }
                        )

        # Search in directory
        elif os.path.isdir(safe_search_path):
            for root, dirs, files in os.walk(safe_search_path):
                # Filter out ignored directories
                dirs[:] = [d for d in dirs if d not in ignore_dirs]

                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, BASE_DIR)

                    # Skip binary files (simple heuristic)
                    if file.endswith(
                        (".pyc", ".so", ".o", ".a", ".exe", ".dll", ".bin")
                    ):
                        continue

                    try:
                        with open(
                            file_path, "r", encoding="utf-8", errors="ignore"
                        ) as f:
                            for line_num, line in enumerate(f, start=1):
                                if regex.search(line):
                                    matches.append(
                                        {
                                            "file": rel_path,
                                            "line": line_num,
                                            "text": line.rstrip()[:500],
                                        }
                                    )
                    except Exception:
                        # Skip files that can't be read
                        continue

        else:
            return {"error": f"{path} is not a file or directory"}

        return {
            "matches": matches[:1000],  # Limit to first 1000 matches
            "count": len(matches),
            "truncated": len(matches) > 1000,
        }

    except Exception as e:
        return {"error": str(e)}


def find(pattern: str, path: str = ".") -> Dict:
    """Find files matching glob pattern.

    Args:
        pattern: Glob pattern (e.g., '*.py', '**/*.js')
        path: Directory to search

    Returns:
        Dict with file list or error
    """
    try:
        safe_search_path = safe_path(path)

        if not os.path.isdir(safe_search_path):
            return {"error": f"{path} is not a directory"}

        # Gitignore patterns to skip
        ignore_dirs = {
            ".git",
            "node_modules",
            "__pycache__",
            ".venv",
            "venv",
            "build",
            "dist",
            ".pytest_cache",
            ".mypy_cache",
        }

        matched_files = []

        # Walk directory tree
        for root, dirs, files in os.walk(safe_search_path):
            # Filter out ignored directories
            dirs[:] = [d for d in dirs if d not in ignore_dirs]

            # Match files
            for file in files:
                if fnmatch.fnmatch(file, pattern):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, BASE_DIR)
                    matched_files.append(rel_path)

        return {
            "files": sorted(matched_files),
            "count": len(matched_files),
        }

    except Exception as e:
        return {"error": str(e)}


def ls(path: str = ".") -> Dict:
    """List directory contents.

    Args:
        path: Directory path

    Returns:
        Dict with files and directories or error
    """
    try:
        safe_dir = safe_path(path)

        if not os.path.isdir(safe_dir):
            return {"error": f"{path} is not a directory"}

        entries = os.listdir(safe_dir)

        files = []
        directories = []

        for entry in sorted(entries):
            entry_path = os.path.join(safe_dir, entry)
            if os.path.isdir(entry_path):
                directories.append(entry)
            else:
                files.append(entry)

        return {
            "files": files,
            "directories": directories,
            "total": len(entries),
        }

    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# Approved Tool Execution (after user approval)
# ============================================================================


def execute_bash_approved(command: str, timeout: int = 120) -> Dict:
    """Execute bash command after user approval.

    Args:
        command: Shell command to execute
        timeout: Timeout in seconds (max 600)

    Returns:
        Dict with stdout/stderr or error
    """
    try:
        # Cap timeout at 10 minutes
        timeout = min(timeout, 600)

        # Execute command
        result = subprocess.run(
            command,
            shell=True,
            cwd=BASE_DIR,  # Run in workspace directory
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,  # No interactive input
        )

        # Truncate output at 100KB
        max_output = 100 * 1024
        stdout = result.stdout[:max_output] if result.stdout else ""
        stderr = result.stderr[:max_output] if result.stderr else ""

        if len(result.stdout or "") > max_output:
            stdout += "\n... [output truncated at 100KB]"
        if len(result.stderr or "") > max_output:
            stderr += "\n... [output truncated at 100KB]"

        return {
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": result.returncode,
            "command": command,
        }

    except subprocess.TimeoutExpired:
        return {
            "error": f"Command timed out after {timeout}s",
            "command": command,
            "exit_code": -1,
        }
    except Exception as e:
        return {"error": str(e), "command": command}


def execute_write_approved(path: str, content: str) -> Dict:
    """Execute write operation after user approval.

    Args:
        path: Path to file
        content: Content to write

    Returns:
        Dict with success status or error
    """
    try:
        safe_file = safe_path(path)

        # Create parent directories
        os.makedirs(os.path.dirname(safe_file) or ".", exist_ok=True)

        # Write file
        with open(safe_file, "w", encoding="utf-8") as f:
            f.write(content)

        return {
            "success": True,
            "message": f"Wrote {len(content)} bytes to {path}",
            "path": path,
        }

    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# Tool Dispatcher
# ============================================================================


def execute_tool(tool_name: str, args: Dict) -> Dict:
    """Route tool calls to the correct Python function.

    Args:
        tool_name: Name of the tool to execute
        args: Arguments for the tool

    Returns:
        Result of the tool execution
    """
    try:
        if tool_name == "read":
            return read(**args)
        elif tool_name == "write":
            return write(**args)
        elif tool_name == "edit":
            return edit(**args)
        elif tool_name == "bash":
            return bash(**args)
        elif tool_name == "grep":
            return grep(**args)
        elif tool_name == "find":
            return find(**args)
        elif tool_name == "ls":
            return ls(**args)
        else:
            return {"error": f"Unknown tool '{tool_name}'"}
    except ValueError as e:
        # Catch sandbox violations from safe_path()
        return {"error": str(e)}
    except TypeError as e:
        # Catch missing/invalid arguments
        return {"error": f"Invalid arguments: {e}"}
