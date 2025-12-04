from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Input
from textual.binding import Binding

from craft_code.config.loader import get_active_model_config
from craft_code.utils import set_base_dir, BASE_DIR
from craft_code.ui.widgets import ChatHistory, StatusLine, LogPanel
from craft_code.core import run_agent
from craft_code.config.prompts import SYSTEM_PROMPT
from openai import OpenAI


class CraftCodeApp(App):
    """Craft Code UI."""

    CSS = """
    /* Tokyo Night Theme Colors */
    * {
        /* Background colors */
        scrollbar-background: #1a1b26;
        scrollbar-color: #414868;
        scrollbar-color-hover: #565f89;
        scrollbar-color-active: #7aa2f7;
    }

    Screen {
        background: #1a1b26;
        color: #c0caf5;
    }

    #main-container {
        width: 100%;
        height: 100%;
        background: #1a1b26;
    }

    #chat-container {
        height: 1fr;
        background: #1a1b26;
        border: none;
        padding: 1 2;
    }

    #input-container {
        height: auto;
        background: #16161e;
        padding: 1 2;
        border-top: solid #414868;
    }

    #chat-input {
        width: 100%;
        background: #1a1b26;
        border: solid #414868;
        color: #c0caf5;
    }

    #chat-input:focus {
        border: solid #7aa2f7;
    }

    #log-panel {
        height: 0;
        display: none;
        background: #1a1b26;
        border-top: solid #414868;
        padding: 1 2;
    }

    #log-panel.visible {
        height: 12;
        display: block;
    }

    .user-message {
        color: #9ece6a;
        padding: 0 0 1 0;
    }

    .assistant-message {
        color: #c0caf5;
        padding: 0 0 1 0;
    }

    .system-message {
        color: #e0af68;
        padding: 0 0 1 0;
        text-style: italic;
    }

    .tool-message {
        color: #565f89;
        padding: 0 0 1 0;
    }

    StatusLine {
        background: #16161e;
        color: #c0caf5;
        height: 1;
        dock: bottom;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("ctrl+l", "toggle_logs", "Logs", show=True),
        Binding("ctrl+r", "clear_chat", "Clear", show=True),
    ]

    def __init__(self, workspace: str = "."):
        """Initialize Craft Code UI.

        Args:
            workspace: Working directory path
        """
        super().__init__()
        self.workspace = workspace
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.client = None
        self.is_processing = False

    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        with Vertical(id="main-container"):
            yield ChatHistory(id="chat-container")
            yield LogPanel(id="log-panel")
            with Container(id="input-container"):
                yield Input(
                    placeholder="Type your message or /exit to quit...", id="chat-input"
                )

        yield StatusLine(id="statusline")

    def on_mount(self) -> None:
        """Initialize the application on mount."""
        set_base_dir(self.workspace)

        cfg = get_active_model_config()
        self.client = OpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"])

        statusline = self.query_one("#statusline", StatusLine)
        statusline.update_config(cfg, BASE_DIR)

        chat = self.query_one("#chat-container", ChatHistory)
        chat.add_system_message("Craft Code started. Type /help for commands.")

        self.query_one("#chat-input", Input).focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user input submission.

        Args:
            event: Input submission event
        """
        if self.is_processing:
            return

        user_input = event.value.strip()
        if not user_input:
            return

        event.input.value = ""

        # Handle commands
        if user_input.startswith("/"):
            await self.handle_command(user_input)
            return

        # Process message
        chat = self.query_one("#chat-container", ChatHistory)
        chat.add_user_message(user_input)

        self.messages.append({"role": "user", "content": user_input})

        self.is_processing = True
        statusline = self.query_one("#statusline", StatusLine)
        statusline.set_processing(True)

        try:
            # Run agent in background
            await self.run_agent_async()
        finally:
            self.is_processing = False
            statusline.set_processing(False)

    async def run_agent_async(self) -> None:
        """Run the agent loop asynchronously."""
        chat = self.query_one("#chat-container", ChatHistory)
        log_panel = self.query_one("#log-panel", LogPanel)

        # Define callback to handle messages from agent
        def message_callback(msg: dict) -> None:
            self.call_from_thread(self.handle_agent_message, msg, chat, log_panel)

        # Define worker function that captures the arguments
        def worker_func():
            return run_agent(
                messages=self.messages,
                client=self.client,
                verbose=False,
                callback=message_callback,
            )

        # Run agent in worker thread
        worker = self.run_worker(worker_func, thread=True)
        self.messages = await worker.wait()

    def handle_agent_message(
        self, message: dict, chat: ChatHistory, log_panel: LogPanel
    ) -> None:
        """Handle messages from the agent.

        Args:
            message: Message dictionary
            chat: ChatHistory widget
            log_panel: LogPanel widget
        """
        if message.get("role") == "assistant":
            content = message.get("content", "")
            if content:
                chat.add_assistant_message(content)

        elif message.get("role") == "tool":
            tool_name = message.get("tool_name", "unknown")
            content = message.get("content", "")
            log_panel.add_log(f"Tool {tool_name}: {content}")

        # Log all messages to log panel
        log_panel.add_log(f"Message: {message}")

    async def handle_command(self, command: str) -> None:
        """Handle slash commands.

        Args:
            command: Command string starting with /
        """
        chat = self.query_one("#chat-container", ChatHistory)

        cmd = command.lower().strip()

        if cmd == "/exit" or cmd == "/quit":
            self.exit()
        elif cmd == "/clear":
            self.action_clear_chat()
        elif cmd == "/help":
            help_text = """Available commands:
            /exit, /quit  Exit Craft Code
            /clear        Clear chat history
            /help         Show this help message
            /logs         Toggle log panel

            Keyboard shortcuts:
            Ctrl+C        Quit
            Ctrl+L        Toggle logs
            Ctrl+R        Clear chat"""
            chat.add_system_message(help_text)
        elif cmd == "/logs":
            self.action_toggle_logs()
        else:
            chat.add_system_message(f"Unknown command: {command}")

    def action_toggle_logs(self) -> None:
        """Toggle the log panel visibility."""
        log_panel = self.query_one("#log-panel", LogPanel)
        log_panel.toggle_class("visible")

    def action_clear_chat(self) -> None:
        """Clear the chat history."""
        chat = self.query_one("#chat-container", ChatHistory)
        chat.clear()
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        chat.add_system_message("Chat history cleared.")

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()
