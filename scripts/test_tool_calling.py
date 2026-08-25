"""Standalone Tool Calling test script with Groq + Qwen."""

import os
import sys
import json

# Set console encoding to UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

from app.llm_client import GroqLLMClient


def get_test_value() -> dict:
    """Mock test tool returning constant value 42."""
    return {"value": 42}


TEST_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_test_value",
            "description": "Returns the secret test value.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
]


def main():
    print("Testing Tool Calling with Groq and Qwen...")
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("[INFO] GROQ_API_KEY not configured. Simulating tool calling loop offline:")
        print("1. Qwen receives question: 'Use the available tool to find the test value.'")
        print("2. Tool request emitted: get_test_value()")
        res = get_test_value()
        print(f"3. Python executed tool -> {res}")
        print(f"4. Expected report: The test value is {res['value']}.")
        return

    try:
        client = GroqLLMClient()
        messages = [
            {"role": "system", "content": "You are a helpful assistant. Use tools when required."},
            {"role": "user", "content": "Use the available tool to find the test value and state it clearly."}
        ]

        response = client.chat(messages=messages, tools=TEST_TOOLS)
        message = response.choices[0].message

        if message.tool_calls:
            print(f"[OK] Qwen requested tool: {message.tool_calls[0].function.name}")
            tool_res = get_test_value()
            messages.append(message.model_dump(exclude_none=True))
            messages.append({
                "role": "tool",
                "tool_call_id": message.tool_calls[0].id,
                "content": json.dumps(tool_res)
            })

            final_resp = client.chat(messages=messages)
            print("Final response from Qwen:")
            print(final_resp.choices[0].message.content)
        else:
            print("Response without tool call:")
            print(message.content)

    except Exception as e:
        print(f"[ERROR] Tool calling test failed: {e}")


if __name__ == "__main__":
    main()
