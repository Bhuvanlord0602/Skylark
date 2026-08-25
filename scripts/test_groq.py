"""Standalone Groq + Qwen connection test script."""

import os
import sys

# Set console encoding to UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

from app.llm_client import GroqLLMClient


def main():
    print("Testing Groq API connection with Qwen model...")
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("[WARNING] GROQ_API_KEY is not set in environment or .env file.")
        return

    try:
        client = GroqLLMClient()
        response = client.chat(
            messages=[
                {
                    "role": "user",
                    "content": "Reply with exactly: Groq connection successful"
                }
            ]
        )
        print("Response from Groq:")
        print(response.choices[0].message.content)
    except Exception as e:
        print(f"[ERROR] Groq connection failed: {e}")


if __name__ == "__main__":
    main()
