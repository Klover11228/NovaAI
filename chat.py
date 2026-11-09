
import customtkinter as ctk
import threading
import os

from tkinter import filedialog, messagebox

from core.ai import ask_ai
from core.long_memory import add_memory, load_memory, extract_memories


class ChatPage(ctk.CTkFrame):

    def __init__(self, parent, chats, active_chat, save_callback):

        super().__init__(parent, fg_color="#171923")

        self.chats = chats
        self.active_chat = active_chat
        self.save_callback = save_callback

        self.streaming_text = ""
        self.streaming_label = None
        self.is_generating = False

        self.long_memory = load_memory()
        self.selected_file = None

        self.title = ctk.CTkLabel(
            self,
            text="Nova AI",
            font=("Inter", 26, "bold")
        )
        self.title.pack(pady=25)

        self.messages = ctk.CTkScrollableFrame(
            self,
            fg_color="#171923"
        )
        self.messages.pack(
            fill="both",
            expand=True,
            padx=25,
            pady=10
        )

        self.file_label = ctk.CTkLabel(
            self,
            text="",
            font=("Inter", 12),
            text_color="#A99AFF"
        )
        self.file_label.pack(pady=(5, 0))

        self.input_frame = ctk.CTkFrame(
            self,
            fg_color="#252838",
            corner_radius=15
        )
        self.input_frame.pack(
            fill="x",
            padx=25,
            pady=25
        )

        self.attach_button = ctk.CTkButton(
            self.input_frame,
            text="Attach",
            width=75,
            height=40,
            fg_color="#383052",
            hover_color="#514274",
            command=self.attach_file
        )
        self.attach_button.pack(
            side="left",
            padx=(10, 0),
            pady=10
        )

        self.entry = ctk.CTkEntry(
            self.input_frame,
            placeholder_text="Message Nova AI...",
            height=45,
            border_width=0
        )
        self.entry.pack(
            side="left",
            fill="x",
            expand=True,
            padx=10,
            pady=10
        )

        self.entry.bind("<Return>", self.on_enter)

        self.send_button = ctk.CTkButton(
            self.input_frame,
            text="Send",
            width=90,
            command=self.send_message
        )
        self.send_button.pack(side="right", padx=10)

        self.show_history()

    def attach_file(self):

        file_path = filedialog.askopenfilename(
            title="Select a file",
            filetypes=[
                ("Supported files", "*.txt *.pdf *.docx *.py *.js *.html *.css *.json *.md *.csv *.xml *.yaml *.yml *.log"),
                ("All files", "*.*")
            ]
        )

        if file_path:

            self.selected_file = file_path

            self.file_label.configure(
                text="Attached: " + os.path.basename(file_path)
            )

    def read_file(self, file_path):

        extension = os.path.splitext(file_path)[1].lower()

        file_size = os.path.getsize(file_path)

        if file_size > 5 * 1024 * 1024:

            raise ValueError(
                "File is too large. Maximum size is 5 MB."
            )

        if extension == ".pdf":

            from pypdf import PdfReader

            reader = PdfReader(file_path)

            content = ""

            for page in reader.pages:

                content += page.extract_text() or ""
                content += "\n"

        elif extension == ".docx":

            from docx import Document

            document = Document(file_path)

            content = "\n".join(
                paragraph.text
                for paragraph in document.paragraphs
            )

        else:

            with open(
                file_path,
                "r",
                encoding="utf-8-sig",
                errors="replace"
            ) as file:

                content = file.read()

        if not content.strip():

            raise ValueError(
                "No readable text found in this file."
            )

        if len(content) > 60000:

            content = content[:60000]

            content += "\n\n[File content was truncated.]"

        return content

    def on_enter(self, event):

        self.send_message()

        return "break"

    def add_message(self, role, content):

        is_user = role == "user"

        row = ctk.CTkFrame(
            self.messages,
            fg_color="transparent"
        )
        row.pack(fill="x", padx=10, pady=7)

        bubble = ctk.CTkFrame(
            row,
            fg_color="#34384F" if is_user else "#242735",
            corner_radius=15
        )
        bubble.pack(
            side="right" if is_user else "left",
            padx=5
        )

        name = "You" if is_user else "Nova AI"

        label = ctk.CTkLabel(
            bubble,
            text=f"{name}\n\n{content}",
            font=("Inter", 14),
            text_color="white",
            justify="left",
            wraplength=650
        )
        label.pack(padx=15, pady=12)

        self.messages.update_idletasks()
        self.messages._parent_canvas.yview_moveto(1.0)

        return label

    def show_history(self):

        for widget in self.messages.winfo_children():
            widget.destroy()

        self.streaming_label = None

        chat = self.chats[self.active_chat]

        self.title.configure(text=chat["title"])

        for message in chat["messages"]:

            self.add_message(
                message["role"],
                message.get(
                    "display_content",
                    message["content"]
                )
            )

    def load_chat(self, chat_id):

        self.active_chat = chat_id

        self.show_history()

    def check_memory_command(self, message):

        lower_message = message.lower()

        triggers = [
            "remember that",
            "remember this",
            "یادت باشه",
            "یادت بمونه",
            "به خاطر بسپار",
            "این رو به خاطر بسپار"
        ]

        for trigger in triggers:

            if trigger in lower_message:

                memory = message[
                    lower_message.find(trigger) + len(trigger):
                ].strip()

                if memory:

                    add_memory(memory)

                    self.long_memory = load_memory()

                    return memory

        return None

    def send_message(self):

        if self.is_generating:
            return

        message = self.entry.get().strip()

        if not message and not self.selected_file:
            return

        chat_id = self.active_chat

        chat = self.chats[chat_id]

        try:

            file_content = ""
            file_name = ""

            if self.selected_file:

                file_name = os.path.basename(
                    self.selected_file
                )

                file_content = self.read_file(
                    self.selected_file
                )

            if not message and file_content:

                message = "Please analyze this file and summarize its content."

            display_message = message

            full_message = message

            if file_content:

                display_message = (
                    f"📎 {file_name}\n\n{message}"
                )

                full_message = (
                    message
                    + "\n\n"
                    + f"Attached file: {file_name}"
                    + "\n\nFILE CONTENT:\n"
                    + file_content
                )

            self.check_memory_command(message)

            if message:

                threading.Thread(
                    target=self.update_memory,
                    args=(message,),
                    daemon=True
                ).start()

            chat["messages"].append({
                "role": "user",
                "content": full_message,
                "display_content": display_message
            })

            if chat["title"] == "New Chat":

                chat["title"] = message[:28] or file_name[:28]

                if len(chat["title"]) > 28:
                    chat["title"] += "..."

                self.title.configure(
                    text=chat["title"]
                )

            self.save_callback()

            self.add_message(
                "user",
                display_message
            )

            self.entry.delete(0, "end")

            self.selected_file = None

            self.file_label.configure(
                text=""
            )

            self.streaming_text = ""

            self.streaming_label = self.add_message(
                "assistant",
                "Thinking..."
            )

            self.is_generating = True

            self.send_button.configure(
                state="disabled",
                text="Thinking..."
            )

            self.attach_button.configure(
                state="disabled"
            )

            history = [
                {
                    "role": item["role"],
                    "content": item["content"]
                }
                for item in chat["messages"]
            ]

            self.long_memory = load_memory()

            if self.long_memory:

                memory_text = "\n".join(
                    f"- {item}" for item in self.long_memory
                )

                history.insert(0, {
                    "role": "system",
                    "content": (
                        "The following information is the user's "
                        "saved long-term memory.\n"
                        "Use it when relevant to answer questions.\n"
                        "Treat it as user-provided information.\n"
                        "Never invent additional personal facts.\n\n"
                        "LONG-TERM MEMORY:\n"
                        + memory_text
                    )
                })

            threading.Thread(
                target=self.get_response,
                args=(history, chat_id),
                daemon=True
            ).start()

        except Exception as error:

            print("SEND ERROR:", error)

            messagebox.showerror(
                "File Error",
                str(error)
            )

            self.is_generating = False

            self.send_button.configure(
                state="normal",
                text="Send"
            )

            self.attach_button.configure(
                state="normal"
            )

    def update_memory(self, message):

        extract_memories(message)

        self.after(
            0,
            self.refresh_memory
        )

    def refresh_memory(self):

        self.long_memory = load_memory()

    def get_response(self, history, chat_id):

        try:

            answer = ask_ai(
                history,
                lambda chunk: self.after(
                    0,
                    self.append_chunk,
                    chunk,
                    chat_id
                )
            )

        except Exception as error:

            answer = f"Error: {error}"

            print("AI ERROR:", error)

        self.after(
            0,
            self.show_response,
            answer,
            chat_id
        )

    def append_chunk(self, chunk, chat_id):

        if self.active_chat != chat_id:
            return

        self.streaming_text += chunk

        if self.streaming_label:

            self.streaming_label.configure(
                text=f"Nova AI\n\n{self.streaming_text}"
            )

            self.messages.update_idletasks()

            self.messages._parent_canvas.yview_moveto(1.0)

    def show_response(self, answer, chat_id):

        chat = self.chats.get(chat_id)

        if chat is not None and not answer.startswith("Error:"):

            chat["messages"].append({
                "role": "assistant",
                "content": answer
            })

            self.save_callback()

        if self.active_chat == chat_id:

            self.show_history()

            if answer.startswith("Error:"):

                self.add_message(
                    "assistant",
                    answer
                )

        self.is_generating = False

        self.send_button.configure(
            state="normal",
            text="Send"
        )

        self.attach_button.configure(
            state="normal"
        )
