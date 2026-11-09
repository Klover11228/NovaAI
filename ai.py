
import requests
import json


def ask_ai(messages, callback=None):

    url = "http://localhost:11434/api/chat"

    system_prompt = """
You are Nova AI, a helpful local AI assistant.

MEMORY RULES:

- Use saved user memories whenever relevant.
- Treat saved memories as facts provided by the user.
- Remember the user's projects, interests and preferences.
- Never invent personal information.
- If you do not know something, say so honestly.
- Respond in the language used by the user.
"""

    memory_messages = []
    conversation = []

    for message in messages:

        if message.get("role") == "system":

            memory_messages.append(
                message.get("content", "")
            )

        else:

            conversation.append(message)

    if memory_messages:

        system_prompt += "\n\n" + "\n\n".join(
            memory_messages
        )

    final_messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    final_messages.extend(conversation)

    data = {
        "model": "qwen3:8b",
        "messages": final_messages,
        "stream": True,
        "options": {
            "temperature": 0.5
        }
    }

    response = requests.post(
        url,
        json=data,
        stream=True,
        timeout=180
    )

    response.raise_for_status()

    full_answer = ""

    try:

        for line in response.iter_lines():

            if not line:
                continue

            result = json.loads(line)

            content = result.get(
                "message", {}
            ).get("content", "")

            if content:

                full_answer += content

                if callback:
                    callback(content)

            if result.get("done"):
                break

    finally:

        response.close()

    return full_answer
