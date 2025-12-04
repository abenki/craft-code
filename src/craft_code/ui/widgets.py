from textual.widgets import Static, RichLog
from textual.containers import VerticalScroll
from rich.text import Text
from rich.markdown import Markdown
from datetime import datetime
import tomllib
from pathlib import Path


class ChatHistory(VerticalScroll):
    """Widget to display chat history with auto-scroll."""

    def __init__(self, **kwargs):
        """Initialize ChatHistory widget.
        
        Args:
            **kwargs: Additional keyword arguments for VerticalScroll
        """
        super().__init__(**kwargs)
        self.can_focus = False

    def add_user_message(self, content: str) -> None:
        """Add a user message to the chat.
        
        Args:
            content: Message content
        """
        #timestamp = datetime.now().strftime("%H:%M:%S")
        text = Text()
        #text.append(f"[{timestamp}] ", style="dim")
        text.append("> ", style="bold #9ece6a")
        text.append(content, style="#c0caf5")
        
        message_widget = Static(text, classes="user-message")
        self.mount(message_widget)
        self.scroll_end(animate=False)

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message to the chat.
        
        Args:
            content: Message content
        """
        #timestamp = datetime.now().strftime("%H:%M:%S")
        text = Text()
        #text.append(f"[{timestamp}] ", style="dim")
        text.append("✦ ", style="bold #7aa2f7")
        
        header_widget = Static(text, classes="assistant-message")
        self.mount(header_widget)
        
        # Render markdown content
        try:
            md = Markdown(content)
            md_widget = Static(md, classes="assistant-message")
            self.mount(md_widget)
        except Exception:
            # Fallback to plain text
            content_text = Text(content, style="#c0caf5")
            plain_widget = Static(content_text, classes="assistant-message")
            self.mount(plain_widget)
        
        self.scroll_end(animate=False)

    def add_system_message(self, content: str) -> None:
        """Add a system message to the chat.
        
        Args:
            content: Message content
        """
        #timestamp = datetime.now().strftime("%H:%M:%S")
        text = Text()
        #text.append(f"[{timestamp}] ", style="dim")
        text.append(" ", style="bold #e0af68")
        text.append(content, style="italic #bb9af7")
        
        message_widget = Static(text, classes="system-message")
        self.mount(message_widget)
        self.scroll_end(animate=False)

    def add_tool_message(self, tool_name: str, content: str) -> None:
        """Add a tool execution message to the chat.
        
        Args:
            tool_name: Name of the tool
            content: Tool output content
        """
        #timestamp = datetime.now().strftime("%H:%M:%S")
        text = Text()
        #text.append(f"[{timestamp}] ", style="dim")
        text.append(f" {tool_name}: ", style="bold #bb9af7")
        text.append(content[:200], style="dim")
        if len(content) > 200:
            text.append("...", style="dim")
        
        message_widget = Static(text, classes="tool-message")
        self.mount(message_widget)
        self.scroll_end(animate=False)

    def clear(self) -> None:
        """Clear all messages from chat history."""
        for child in list(self.children):
            child.remove()


class StatusLine(Static):
    """Neovim-style status line at the bottom."""

    def __init__(self, **kwargs):
        """Initialize StatusLine widget.
        
        Args:
            **kwargs: Additional keyword arguments for Static
        """
        super().__init__("", **kwargs)
        self.provider = "unknown"
        self.model = "unknown"
        self.workspace = "."
        self.processing = False
        self.version = self._get_version()

    def _get_version(self) -> str:
        """Get Craft Code version from pyproject.toml.
        
        Returns:
            Version string
        """
        try:
            pyproject_path = Path(__file__).parent.parent.parent.parent / "pyproject.toml"
            if pyproject_path.exists():
                with open(pyproject_path, "rb") as f:
                    pyproject = tomllib.load(f)
                    return pyproject["project"]["version"]
        except Exception:
            pass
        return "unknown"

    def update_config(self, config: dict, workspace: str) -> None:
        """Update configuration display.
        
        Args:
            config: Configuration dictionary
            workspace: Workspace path
        """
        self.provider = config.get("provider", "unknown")
        self.model = config.get("model", "unknown")
        self.workspace = workspace
        self.refresh_display()

    def set_processing(self, processing: bool) -> None:
        """Set processing status.
        
        Args:
            processing: Whether the agent is processing
        """
        self.processing = processing
        self.refresh_display()

    def refresh_display(self) -> None:
        """Refresh the status display."""
        status_text = "processing" if self.processing else "ready"
        status_color = "#e0af68" if self.processing else "#9ece6a"
        
        content = Text()
        
        # Left section: app name and version
        content.append(" Craft Code ", style="bold #7aa2f7")
        content.append(f"v{self.version}", style="dim")
        
        # Middle section: status
        content.append(" │ ", style="dim")
        content.append(status_text, style=status_color)
        
        # Right section: provider, model, workspace
        content.append(" │ ", style="dim")
        content.append(f"{self.provider}", style="#bb9af7")
        content.append(" • ", style="dim")
        content.append(f"{self.model}", style="#7aa2f7")
        content.append(" │ ", style="dim")
        content.append(f"{self.workspace}", style="dim")
        
        self.update(content)


class LogPanel(RichLog):
    """Widget to display debug logs."""

    def __init__(self, **kwargs):
        """Initialize LogPanel widget.
        
        Args:
            **kwargs: Additional keyword arguments for RichLog
        """
        super().__init__(**kwargs)
        self.max_lines = 1000

    def add_log(self, message: str) -> None:
        """Add a log entry.
        
        Args:
            message: Log message
        """
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.write(Text(f"[{timestamp}] {message}", style="#565f89"))
