import customtkinter as ctk

from ui.chat import ChatPage
from ui.sidebar import Sidebar
from core.memory import load_chats, save_chats


class NovaAI(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("Nova AI")
        self.geometry("1200x750")
        self.minsize(900, 600)

        self.chats = load_chats()

        if not self.chats:
            self.chats["chat_1"] = {
                "title": "New Chat",
                "messages": []
            }

        self.active_chat = list(self.chats.keys())[-1]

        self.sidebar = Sidebar(
            self,
            self.new_chat,
            self.select_chat,
            self.delete_chat
        )

        self.sidebar.pack(side="left", fill="y")

        self.chat_page = ChatPage(
            self,
            self.chats,
            self.active_chat,
            self.save_data
        )

        self.chat_page.pack(
            side="right",
            fill="both",
            expand=True
        )

        self.update_sidebar()

    def save_data(self):
        save_chats(self.chats)

    def update_sidebar(self):
        self.sidebar.update_chats(
            self.chats,
            self.active_chat
        )

    def new_chat(self):

        number = 1

        while f"chat_{number}" in self.chats:
            number += 1

        chat_id = f"chat_{number}"

        self.chats[chat_id] = {
            "title": "New Chat",
            "messages": []
        }

        self.active_chat = chat_id

        self.chat_page.load_chat(chat_id)

        self.save_data()
        self.update_sidebar()

    def select_chat(self, chat_id):

        self.active_chat = chat_id

        self.chat_page.load_chat(chat_id)

        self.update_sidebar()

    def delete_chat(self, chat_id):

        if len(self.chats) == 1:
            return

        del self.chats[chat_id]

        if self.active_chat == chat_id:

            self.active_chat = list(self.chats.keys())[-1]

            self.chat_page.load_chat(self.active_chat)

        self.save_data()
        self.update_sidebar()


ctk.set_appearance_mode("dark")

app = NovaAI()
app.mainloop()