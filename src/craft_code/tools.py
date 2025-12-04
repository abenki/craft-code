import os
import re
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
]


def list_directory(path):
    """List files in the given directory.

    Args:
        path (str): Path to the directory.

    Returns:
        list: List of files in the directory.
    """
    try:
        safe_dir = safe_path(path)
        return os.listdir(safe_dir)
    except Exception as e:
        return {"error": str(e)}


def read_file(path):
    """Read the contents of a text file safely (max 20KB).

    Args:
        path (str): Path to the file.

    Returns:
        str: Contents of the file.
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


def search_in_file(path, pattern):
    """Search for a regex or keyword inside a file and return matching lines.

    Args:
        path (str): Path to the file.
        pattern (str): Regex pattern or keyword to search for.

    Returns:
        dict: Matches found with line numbers.
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


def write_file(path, content):
    """Write or overwrite a file with new content.

    Args:
        path (str): Path to the file.
        content (str): Text content to write.

    Returns:
        dict: Success message or error details.
    """
    try:
        safe_file = safe_path(path)
        os.makedirs(os.path.dirname(safe_file), exist_ok=True)
        with open(safe_file, "w", encoding="utf-8") as f:
            f.write(content)
        return {"success": True, "message": f"Wrote {len(content)} bytes to {path}"}
    except Exception as e:
        return {"error": str(e)}


def execute_tool(tool_name, args):
    """Route tool calls to the correct Python function with sandbox enforcement.
    Args:
        tool_name (str): Name of the tool to execute.
        args (dict): Arguments for the tool.
    """
    try:
        if tool_name == "list_directory":
            return list_directory(**args)
        elif tool_name == "read_file":
            return read_file(**args)
        elif tool_name == "search_in_file":
            return search_in_file(**args)
        elif tool_name == "write_file":
            return write_file(**args)
        else:
            return {"error": f"Unknown tool '{tool_name}'"}
    except ValueError as e:
        # Catch sandbox violations
        return {"error": str(e)}
