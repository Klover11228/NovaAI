
import os
import json
import re
import requests


BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

MEMORY_FILE = os.path.join(
    BASE_DIR,
    "data",
    "long_memory.json"
)


def load_memory():

    if not os.path.exists(MEMORY_FILE):
        return []

    try:

        with open(MEMORY_FILE, "r", encoding="utf-8") as file:
            memories = json.load(file)

        if isinstance(memories, list):
            return memories

        return []

    except Exception as error:

        print("Memory loading error:", error)
        return []


def save_memory(memories):

    os.makedirs(
        os.path.dirname(MEMORY_FILE),
        exist_ok=True
    )

    with open(MEMORY_FILE, "w", encoding="utf-8") as file:

        json.dump(
            memories,
            file,
            ensure_ascii=False,
            indent=4
        )


def get_memory_category(memory):

    memory = memory.strip()

    patterns = [
        r"i am learning\s+(.+)",
        r"i'm learning\s+(.+)",
        r"learning\s+(.+)",
        r"i learn\s+(.+)",
        r"i am studying\s+(.+)",
        r"i'm studying\s+(.+)"
    ]

    for pattern in patterns:

        match = re.fullmatch(
            pattern,
            memory,
            re.IGNORECASE
        )

        if match:

            value = match.group(1).strip()

            value = re.sub(
                r"\s+(now|these days|currently)$",
                "",
                value,
                flags=re.IGNORECASE
            )

            return "learning_language", value

    return None, None


def add_memory(memory):

    if not isinstance(memory, str):
        return False

    memory = memory.strip()

    if not memory:
        return False

    memories = load_memory()

    new_category, new_value = get_memory_category(
        memory
    )

    if new_category:

        matching_indexes = []

        for index, old_memory in enumerate(memories):

            old_category, old_value = get_memory_category(
                old_memory
            )

            if old_category == new_category:
                matching_indexes.append(index)

        if matching_indexes:

            first_index = matching_indexes[0]

            old_value = get_memory_category(
                memories[first_index]
            )[1]

            if old_value.lower() == new_value.lower():

                print("Duplicate memory detected.")
                return False

            memories[first_index] = memory

            for index in reversed(matching_indexes[1:]):
                memories.pop(index)

            save_memory(memories)

            print("Memory updated.")
            return True

        memories.append(memory)

        save_memory(memories)

        print("New memory saved.")
        return True

    for old_memory in memories:

        if memory.lower() == old_memory.lower():

            print("Duplicate memory detected.")
            return False

    memories.append(memory)

    save_memory(memories)

    print("New memory saved.")
    return True


def extract_memories(message):

    prompt = f"""
You are Nova AI's long-term memory extractor.

Extract useful and stable information about the user.

Rules:
- Save long-term preferences.
- Save interests and projects.
- Save programming languages the user is learning.
- Ignore temporary questions.
- Ignore greetings.
- Do not save sensitive personal information.
- Do not invent facts.

Return only JSON.

Format:
{{"memories":["fact 1","fact 2"]}}

User message:
{message}
"""

    try:

        response = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": "qwen3:8b",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "stream": False,
                "format": "json",
                "think": False
            },
            timeout=120
        )

        response.raise_for_status()

        result = response.json()

        answer = json.loads(
            result["message"]["content"]
        )

        new_memories = answer.get("memories", [])

        if not isinstance(new_memories, list):
            return []

        saved = []

        for memory in new_memories:

            if add_memory(memory):
                saved.append(memory)

        return saved

    except Exception as error:

        print("Memory extraction error:", error)
        return []
