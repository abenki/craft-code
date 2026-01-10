# Craft Code

A local terminal coding agent that can explore, analyze, and modify your codebase through structured tool calls.
Chat with your codebase — locally and privately.

![Craft Code screenshot](/docs/assets/craft-code-screenshot.png "Craft Code Screenshot")

## 🚀 Installation
Craft Code runs locally with your own LLM setup. But if you prefer, you can use an API key from providers like OpenAI or Mistral AI, or any provider supporting OpenAI-style endpoints.

Prerequisites:
- [uv](https://docs.astral.sh/uv/#highlights)
- [LM Studio](https://lmstudio.ai/), [Ollama](https://ollama.com/), or an API key from OpenAI/Mistral AI

### 1. Clone the repository and install Craft Code
```bash
git clone git@github.com:abenki/craft-code.git
cd craft-code
uv tool install .
craft-code --version
```
This installs the `craft-code` command globally in your system path.

### 2. Configure Craft Code

By default, Craft Code will connect to an LM Studio server running at http://localhost:1234/v1. To switch provider or customize settings, run:

```bash
craft-code configure
```

This will create / edit your configuration file at: ```~/.config/craft-code/config.toml```


Example content:
```toml
provider = "lm_studio"

[models.lm_studio]
base_url = "http://localhost:1234/v1"
model = "qwen/qwen3-4b-2507"
api_key = "lm-studio"

[models.ollama]
base_url = "http://localhost:11434/v1"
model = "qwen3:4b"
api_key = "ollama"

[models.openai]
base_url = "https://api.openai.com/v1"
model = "gpt-5"
api_key = ""

[models.mistral]
base_url = "https://api.mistral.ai/v1"
model = "devstral-small-latest"
api_key = ""
```

### 3. Updating or deleting the app
To update Craft Code, first run `git pull` in your local craft-code repository, then run `uv tool upgrade craft-code`.

If you wish to delete Craft Code, simply run `uv tool uninstall craft-code` and optionally `uv cache clean`.

## 🧑‍💻 Usage

### Launch the app you want to use for LLM serving
- **LM Studio**: Launch the app, load the model you want to use and start the server.
- **Ollama**: Run `ollama serve` from your terminal.
- **OpenAI/Mistral AI**: No local setup needed, just configure your API key using `craft-code configure`.

### Start Craft Code
To start an interactive session:
```bash
craft-code
```
     
This launches the TUI where you can chat with your codebase. Type your questions and Craft Code will respond step-by-step using the available tools.

### CLI Options and commands
| Flag               | Description                                  |
| ------------------ | -------------------------------------------- |
| `configure`        | Launch interactive configuration wizard      |
| `-v, --version`    | Show current Craft Code version              |


## 🔐 Security & Safety

- All paths are validated to prevent directory traversal.
- All file operations are sandboxed — Craft Code cannot access files outside the workspace.

Example: if you run `craft-code` inside `/Users/bob/projects/my-app`, it cannot access files outside that folder.


## 🚧 Agent Limitations

Craft Code has the following limitations:
- The maximum file size that can be read is 20KB.
- The agent cannot perform complex operations, such as refactoring or debugging.


## 🎨 UI Features

Craft Code includes a terminal user interface (TUI) with:
- **Chat interface** with syntax-highlighted markdown responses
- **Status bar** showing model, provider, and workspace info
- **Log panel** for debugging (toggle with `Ctrl+L`)
- **Keyboard shortcuts**:
  - `Ctrl+C` - Quit
  - `Ctrl+L` - Toggle logs
  - `Ctrl+R` - Clear chat
- **Slash commands**:
  - `/help` - Show available commands
  - `/clear` - Clear chat history
  - `/logs` - Toggle log panel
  - `/exit` or `/quit` - Exit Craft Code


## 🛠️ Supported Tools

Craft Code uses a minimal, powerful toolset inspired by Unix philosophy:

### Core Tools (Modify Codebase)
| Tool    | Description                                                                  |
| ------- | ---------------------------------------------------------------------------- |
| `read`  | Read file contents with pagination (offset/limit for large files, max 20KB) |
| `write` | Write or overwrite files (creates parent directories automatically)          |
| `edit`  | Replace exact text in files (must match exactly, fails if ambiguous)         |
| `bash`  | Execute shell commands (git, tests, builds, package management, etc.)        |

### Read-Only Tools (Explore Codebase)
| Tool   | Description                                                |
| ------ | ---------------------------------------------------------- |
| `grep` | Search for text/regex patterns in files (recursive)        |
| `find` | Find files by glob pattern (e.g., `*.py`, `**/*.js`)       |
| `ls`   | List directory contents including files and subdirectories |

**Key Features:**
- All operations are sandboxed to workspace directory
- `bash` tool enables git operations, testing, building, and package management
- Dangerous commands (sudo, rm -rf /, etc.) require user approval
- File paths are relative to workspace root


## 💻 Dev workflow

If you want to run Craft Code in development mode:
```bash
git clone git@github.com:abenki/craft-code.git
cd craft-code
uv sync
uv pip install -e .
uv run -m craft_code.cli
```

This lets you test new features and modify the source code directly.
