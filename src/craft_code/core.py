import json
from typing import Callable, Optional
from craft_code.tools import tools, execute_tool
from craft_code.utils import debug_log
from craft_code.config.loader import get_active_model_config


def run_agent(
    messages, client=None, verbose=False, callback: Optional[Callable] = None
):
    """Run the agent loop until the model produces a final answer.

    Args:
        messages: List of conversation messages
        client: OpenAI client instance
        verbose: Enable verbose logging
        callback: Optional callback function to handle intermediate messages

    Returns:
        Updated messages list
    """
    if client is None:
        raise ValueError("OpenAI client must be provided.")

    if verbose:
        debug_log("STEP 1 — Initial messages", messages)

    config = get_active_model_config()
    model = config["model"]

    while True:
        response = client.chat.completions.create(
            model=model,
            tools=tools,
            messages=messages,
        )

        message = response.choices[0].message
        if verbose:
            debug_log("MODEL RESPONSE", message.model_dump())

        # Execute all tool calls
        if message.tool_calls:
            messages.append(message)

            for tool_call in message.tool_calls:
                # Handle both object-style (OpenAI) and dict-style (Mistral) tool calls
                if isinstance(tool_call, dict):
                    tool_name = tool_call["function"]["name"]
                    args = json.loads(tool_call["function"]["arguments"])
                    tool_call_id = tool_call["id"]
                else:
                    tool_name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)
                    tool_call_id = tool_call.id

                if verbose:
                    debug_log(f"EXECUTING TOOL: {tool_name}", args)

                tool_output = execute_tool(tool_name, args)

                if verbose:
                    debug_log(f"TOOL OUTPUT ({tool_name})", tool_output)

                # Notify callback about tool execution
                if callback:
                    callback(
                        {
                            "role": "tool",
                            "tool_name": tool_name,
                            "content": json.dumps(tool_output),
                        }
                    )

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": json.dumps(tool_output),
                    }
                )

            # Continue looping for possible multi-step tool calls
            continue

        # No more tool calls -> final answer
        if message.content:
            if verbose:
                debug_log("FINAL ANSWER", message.content)
                print("\n✅ FINAL ANSWER:\n" + "-" * 80)
            print(message.content)

            final_message = {"role": "assistant", "content": message.content}
            messages.append(final_message)

            # Notify callback about final message
            if callback:
                callback(final_message)

            return messages

        # Safety guard
        if response.choices[0].finish_reason == "stop":
            if not callback:
                print("Model ended without content.")
            return messages
