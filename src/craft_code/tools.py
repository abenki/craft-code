import os
import re
import fnmatch
from typing import List, Dict
from craft_code.utils import safe_path

# Tool definitions
tools = [
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files in a directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to directory"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory_recursive",
            "description": "Recursively list all files in a directory tree, with optional glob pattern filtering (e.g., '*.py', '*.{js,ts}'). Automatically excludes common directories like .git, node_modules, __pycache__, .venv, build, dist.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Root directory path to start listing from",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Optional glob pattern to filter files (e.g., '*.py', '*.md'). Defaults to '*' (all files).",
                    },
                    "exclude_dirs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of directory names to exclude. Defaults to common directories like .git, node_modules, etc.",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a text file (max 20KB).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_in_file",
            "description": "Search for a keyword or regex pattern in a file and return matching lines.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file"},
                    "pattern": {
                        "type": "string",
                        "description": "Regex or keyword to search for",
                    },
                },
                "required": ["path", "pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write or overwrite content to a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file"},
                    "content": {
                        "type": "string",
                        "description": "Text content to write",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "append_to_file",
            "description": "Append content to the end of an existing file without overwriting. Creates the file if it doesn't exist.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file"},
                    "content": {
                        "type": "string",
                        "description": "Text content to append",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "replace_in_file",
            "description": "Find and replace text in a file using regex pattern. Returns the number of replacements made.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file"},
                    "pattern": {
                        "type": "string",
                        "description": "Regex pattern to find",
                    },
                    "replacement": {
                        "type": "string",
                        "description": "Text to replace matches with",
                    },
                    "count": {
                        "type": "integer",
                        "description": "Maximum number of replacements (0 = replace all). Defaults to 0.",
                    },
                },
                "required": ["path", "pattern", "replacement"],
            },
        },
    },
]


def list_directory(path: str) -> List:
    """List files in the given directory.

    Args:
        path: Path to the directory.

    Returns:
        List of files in the directory.
    """
    try:
        safe_dir = safe_path(path)
        return os.listdir(safe_dir)
    except Exception as e:
        return {"error": str(e)}


def list_directory_recursive(
    path: str, pattern: str = "*", exclude_dirs: List[str] = None
) -> Dict:
    """Recursively list all files in a directory tree with optional filtering.

    Args:
        path: Root directory path to start listing from.
        pattern: Optional glob pattern to filter files (e.g., '*.py', '*.md').
        exclude_dirs: List of directory names to exclude.

    Returns:
        Dictionary with list of matching file paths relative to the root.
    """
    if exclude_dirs is None:
        exclude_dirs = [
            ".git",
            "node_modules",
            "__pycache__",
            ".venv",
            "build",
            "dist",
            ".pytest_cache",
            ".mypy_cache",
            "venv",
            "env",
        ]

    try:
        safe_dir = safe_path(path)
        matched_files = []

        for root, dirs, files in os.walk(safe_dir):
            # Filter out excluded directories in-place
            dirs[:] = [d for d in dirs if d not in exclude_dirs]

            # Match files against pattern
            for file in files:
                if fnmatch.fnmatch(file, pattern):
                    # Get relative path from the starting directory
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, safe_dir)
                    matched_files.append(rel_path)

        return {
            "files": sorted(matched_files),
            "count": len(matched_files),
            "pattern": pattern,
        }
    except Exception as e:
        return {"error": str(e)}


def read_file(path: str) -> Dict:
    """Read the contents of a text file safely (max 20KB).

    Args:
        path: Path to the file.

    Returns:
        Contents of the file.
    """
    try:
        safe_file = safe_path(path)
        if not os.path.isfile(safe_file):
            return {"error": f"{path} is not a file."}

        # Limit file size to prevent overload
        max_size = 20 * 1024  # 20 KB
        size = os.path.getsize(safe_file)
        if size > max_size:
            return {"error": f"File too large ({size} bytes). Max allowed: {max_size}."}

        with open(safe_file, "r", encoding="utf-8", errors="ignore") as f:
            return {"content": f.read()}
    except Exception as e:
        return {"error": str(e)}


def search_in_file(path: str, pattern: str) -> Dict:
    """Search for a regex or keyword inside a file and return matching lines.

    Args:
        path: Path to the file.
        pattern: Regex pattern or keyword to search for.

    Returns:
        Matches found with line numbers.
    """
    try:
        safe_file = safe_path(path)
        if not os.path.isfile(safe_file):
            return {"error": f"{path} is not a file."}

        results = []
        regex = re.compile(pattern, re.IGNORECASE)
        with open(safe_file, "r", encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f, start=1):
                if regex.search(line):
                    results.append({"line": i, "text": line.strip()})
        return {"matches": results, "count": len(results)}
    except re.error:
        return {"error": f"Invalid regex pattern: {pattern}"}
    except Exception as e:
        return {"error": str(e)}


def write_file(path: str, content: str) -> Dict:
    """Write or overwrite a file with new content.

    Args:
        path: Path to the file.
        content: Text content to write.

    Returns:
        Success message or error details.
    """
    try:
        safe_file = safe_path(path)
        os.makedirs(os.path.dirname(safe_file), exist_ok=True)
        with open(safe_file, "w", encoding="utf-8") as f:
            f.write(content)
        return {"success": True, "message": f"Wrote {len(content)} bytes to {path}"}
    except Exception as e:
        return {"error": str(e)}


def append_to_file(path: str, content: str) -> Dict:
    """Append content to the end of a file without overwriting.

    Args:
        path: Path to the file.
        content: Text content to append.

    Returns:
        Success message or error details.
    """
    try:
        safe_file = safe_path(path)
        os.makedirs(os.path.dirname(safe_file), exist_ok=True)

        # Create file if it doesn't exist
        mode = "a" if os.path.exists(safe_file) else "w"

        with open(safe_file, mode, encoding="utf-8") as f:
            f.write(content)

        return {
            "success": True,
            "message": f"Appended {len(content)} bytes to {path}",
        }
    except Exception as e:
        return {"error": str(e)}


def replace_in_file(path: str, pattern: str, replacement: str, count: int = 0) -> Dict:
    """Find and replace text in a file using regex pattern.

    Args:
        path: Path to the file.
        pattern: Regex pattern to find.
        replacement: Text to replace matches with.
        count: Maximum number of replacements (0 = replace all).

    Returns:
        Success message with replacement count or error details.
    """
    try:
        safe_file = safe_path(path)
        if not os.path.isfile(safe_file):
            return {"error": f"{path} is not a file."}

        # Read file content
        with open(safe_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Perform replacement
        regex = re.compile(pattern)
        new_content, num_replacements = regex.subn(replacement, content, count=count)

        # Write back if changes were made
        if num_replacements > 0:
            with open(safe_file, "w", encoding="utf-8") as f:
                f.write(new_content)

        return {
            "success": True,
            "replacements": num_replacements,
            "message": f"Made {num_replacements} replacement(s) in {path}",
        }
    except re.error:
        return {"error": f"Invalid regex pattern: {pattern}"}
    except Exception as e:
        return {"error": str(e)}


def execute_tool(tool_name: str, args: Dict) -> Dict:
    """Route tool calls to the correct Python function with sandbox enforcement.

    Args:
        tool_name: Name of the tool to execute.
        args: Arguments for the tool.

    Returns:
        Result of the tool execution.
    """
    try:
        if tool_name == "list_directory":
            return list_directory(**args)
        elif tool_name == "list_directory_recursive":
            return list_directory_recursive(**args)
        elif tool_name == "read_file":
            return read_file(**args)
        elif tool_name == "search_in_file":
            return search_in_file(**args)
        elif tool_name == "write_file":
            return write_file(**args)
        elif tool_name == "append_to_file":
            return append_to_file(**args)
        elif tool_name == "replace_in_file":
            return replace_in_file(**args)
        else:
            return {"error": f"Unknown tool '{tool_name}'"}
    except ValueError as e:
        # Catch sandbox violations
        return {"error": str(e)}
