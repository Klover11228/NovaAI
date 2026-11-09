import json
import os


FILE_PATH = "data/chats.json"
OLD_FILE = "data/history.json"


def load_chats():

    os.makedirs("data", exist_ok=True)

    if os.path.exists(FILE_PATH):

        with open(FILE_PATH, "r", encoding="utf-8") as file:
            chats = json.load(file)

        for chat_id in chats:

            if isinstance(chats[chat_id], list):

                chats[chat_id] = {
                    "title": "New Chat",
                    "messages": chats[chat_id]
                }

        return chats

    if os.path.exists(OLD_FILE):

        with open(OLD_FILE, "r", encoding="utf-8") as file:
            history = json.load(file)

        chats = {
            "chat_1": {
                "title": "Previous Chat",
                "messages": history
            }
        }

    else:

        chats = {
            "chat_1": {
                "title": "New Chat",
                "messages": []
            }
        }

    save_chats(chats)

    return chats


def save_chats(chats):

    os.makedirs("data", exist_ok=True)

    with open(FILE_PATH, "w", encoding="utf-8") as file:

        json.dump(
            chats,
            file,
            ensure_ascii=False,
            indent=4
        )