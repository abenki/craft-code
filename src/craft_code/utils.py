from datetime import datetime
import json
import os

BASE_DIR = os.getcwd()


def debug_log(title, data=None):
    """Pretty-print debugging information safely.

    Args:
        title (str): Title for the log section.
        data (any, optional): Data to be logged. Defaults to None.
    """
    print("\n" + "=" * 80)
    print(f"🧠 {title} - {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 80)
    if data is not None:
        try:
            print(json.dumps(data, indent=2))
        except Exception:
            try:
                if hasattr(data, "model_dump"):
                    print(json.dumps(data.model_dump(), indent=2))
                else:
                    print(str(data))
            except Exception:
                print(str(data))
    print()


def safe_path(path: str) -> str:
    """
    Resolve a path and ensure it stays inside BASE_DIR.

    Args:
        path (str): User-supplied path (absolute or relative)

    Returns:
        str: Absolute safe path

    Raises:
        ValueError: If the path escapes BASE_DIR
    """
    # Resolve relative paths and symbolic links
    full_path = os.path.realpath(os.path.join(BASE_DIR, path))

    # Check if resolved path is inside BASE_DIR
    if not full_path.startswith(BASE_DIR):
        raise ValueError(
            f"Access denied: '{full_path}' is outside the allowed working directory ({BASE_DIR})."
        )

    return full_path


def rel_path(path: str) -> str:
    """Return the path relative to BASE_DIR."""
    from .utils import BASE_DIR

    return os.path.relpath(path, BASE_DIR)


def set_base_dir(path: str):
    """Set the base working directory for Craft Code."""
    global BASE_DIR
    BASE_DIR = os.path.realpath(path)
    print(f"📁 Workspace set to: {BASE_DIR}")
