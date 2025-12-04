from openai import OpenAI
import json
import os
from datetime import datetime

client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")

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
]


def list_directory(path):
    try:
        return os.listdir(path)
    except Exception as e:
        return {"error": str(e)}


def execute_tool(tool_name, args):
    """Route tool calls to the correct Python function."""
    if tool_name == "list_directory":
        return list_directory(**args)
    else:
        return {"error": f"Unknown tool '{tool_name}'"}


def debug_log(title, data=None):
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


# -----------------------------------------------------------------------------
# Start conversation
# -----------------------------------------------------------------------------
messages = [
    {
        "role": "system",
        "content": "You are an assistant that can make changes to a codebase.",
    },
    {"role": "user", "content": "List all files in the data folder."},
]

debug_log("STEP 1 — Initial messages", messages)

while True:
    response = client.chat.completions.create(
        model="qwen/qwen3-4b-2507",
        tools=tools,
        messages=messages,
    )

    message = response.choices[0].message
    debug_log("MODEL RESPONSE", message.model_dump())

    # If the model calls tools, execute them all
    if message.tool_calls:
        messages.append(message)
        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            debug_log(f"EXECUTING TOOL: {tool_name}", args)

            tool_output = execute_tool(tool_name, args)
            debug_log(f"TOOL OUTPUT ({tool_name})", tool_output)

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_output),
                }
            )

        # Continue looping — model may request another tool next turn
        continue

    # No tool calls? Then we’ve reached the final answer.
    if message.content:
        debug_log("FINAL ANSWER", message.content)
        print("\n✅ FINAL ANSWER:\n" + "-" * 80)
        print(message.content)
        break

    # Safety guard
    if response.choices[0].finish_reason == "stop":
        print("Model ended without content.")
        break
