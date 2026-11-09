
import customtkinter as ctk

from core.long_memory import load_memory, save_memory, add_memory


class Sidebar(ctk.CTkFrame):

    def __init__(self, parent, new_chat_command,
                 select_chat_command, delete_chat_command):

        super().__init__(
            parent,
            width=270,
            fg_color="#11131D",
            corner_radius=0
        )

        self.new_chat_command = new_chat_command
        self.select_chat_command = select_chat_command
        self.delete_chat_command = delete_chat_command

        self.pack_propagate(False)

        title = ctk.CTkLabel(
            self,
            text="NOVA AI",
            font=("Inter", 25, "bold"),
            text_color="#8B7CFF"
        )
        title.pack(pady=(30, 25))

        new_chat = ctk.CTkButton(
            self,
            text="+ New Chat",
            height=42,
            corner_radius=10,
            fg_color="#292C3D",
            hover_color="#383B52",
            command=self.new_chat_command
        )
        new_chat.pack(padx=15, fill="x")

        memory_button = ctk.CTkButton(
            self,
            text="Memory Manager",
            height=42,
            corner_radius=10,
            fg_color="#383052",
            hover_color="#514274",
            command=self.open_memory_manager
        )
        memory_button.pack(padx=15, fill="x", pady=(10, 0))

        label = ctk.CTkLabel(
            self,
            text="YOUR CONVERSATIONS",
            font=("Inter", 11, "bold"),
            text_color="#777B91"
        )
        label.pack(anchor="w", padx=18, pady=(25, 10))

        self.chat_list = ctk.CTkScrollableFrame(
            self,
            fg_color="#11131D"
        )
        self.chat_list.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=(0, 15)
        )

    def get_category(self, memory):

        text = memory.lower()

        programming_words = [
            "python", "javascript", "java",
            "programming", "coding", "developer",
            "programmer", "learning", "studying"
        ]

        project_words = [
            "project", "nova ai", "nova meet",
            "application", "app", "website"
        ]

        preference_words = [
            "favorite", "prefer", "like",
            "love", "interest", "hobby"
        ]

        if any(word in text for word in project_words):
            return "Projects"

        if any(word in text for word in programming_words):
            return "Programming"

        if any(word in text for word in preference_words):
            return "Preferences"

        return "Personal"

    def open_memory_manager(self):

        window = ctk.CTkToplevel(self)
        window.title("Nova AI - Memory Manager")
        window.geometry("700x650")
        window.configure(fg_color="#171923")
        window.transient(self.winfo_toplevel())

        title = ctk.CTkLabel(
            window,
            text="Memory Manager",
            font=("Inter", 25, "bold"),
            text_color="#8B7CFF"
        )
        title.pack(pady=(20, 5))

        description = ctk.CTkLabel(
            window,
            text="Manage your long-term memories",
            font=("Inter", 12),
            text_color="#9296AA"
        )
        description.pack(pady=(0, 15))

        self.memory_list = ctk.CTkScrollableFrame(
            window,
            fg_color="#171923"
        )
        self.memory_list.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=10
        )

        add_frame = ctk.CTkFrame(
            window,
            fg_color="#252838",
            corner_radius=12
        )
        add_frame.pack(
            fill="x",
            padx=20,
            pady=15
        )

        self.memory_entry = ctk.CTkEntry(
            add_frame,
            placeholder_text="Write a new memory...",
            height=40,
            border_width=0
        )
        self.memory_entry.pack(
            side="left",
            fill="x",
            expand=True,
            padx=10,
            pady=10
        )

        add_button = ctk.CTkButton(
            add_frame,
            text="Add",
            width=70,
            command=self.add_new_memory
        )
        add_button.pack(side="right", padx=10)

        self.refresh_memories()

    def refresh_memories(self):

        for widget in self.memory_list.winfo_children():
            widget.destroy()

        memories = load_memory()

        categories = {
            "Projects": [],
            "Programming": [],
            "Preferences": [],
            "Personal": []
        }

        for index, memory in enumerate(memories):

            category = self.get_category(memory)

            categories[category].append(
                (index, memory)
            )

        for category, items in categories.items():

            if not items:
                continue

            section = ctk.CTkLabel(
                self.memory_list,
                text=f"{category} ({len(items)})",
                font=("Inter", 17, "bold"),
                text_color="#8B7CFF"
            )
            section.pack(
                anchor="w",
                pady=(18, 8),
                padx=5
            )

            for index, memory in items:

                row = ctk.CTkFrame(
                    self.memory_list,
                    fg_color="#252838",
                    corner_radius=10
                )
                row.pack(fill="x", pady=5)

                memory_label = ctk.CTkLabel(
                    row,
                    text=memory,
                    font=("Inter", 12),
                    text_color="white",
                    wraplength=350,
                    justify="left"
                )
                memory_label.pack(
                    side="left",
                    fill="x",
                    expand=True,
                    padx=10,
                    pady=12
                )

                edit_button = ctk.CTkButton(
                    row,
                    text="Edit",
                    width=55,
                    command=lambda i=index, old=memory:
                        self.edit_memory(i, old)
                )
                edit_button.pack(side="right", padx=3)

                delete_button = ctk.CTkButton(
                    row,
                    text="X",
                    width=35,
                    fg_color="#8B303D",
                    hover_color="#A83B4B",
                    command=lambda i=index:
                        self.delete_memory(i)
                )
                delete_button.pack(side="right", padx=5)

        if not memories:

            empty_label = ctk.CTkLabel(
                self.memory_list,
                text="No memories saved yet.",
                text_color="#9296AA"
            )
            empty_label.pack(pady=30)

    def add_new_memory(self):

        memory = self.memory_entry.get().strip()

        if not memory:
            return

        add_memory(memory)

        self.memory_entry.delete(0, "end")

        self.refresh_memories()

    def edit_memory(self, index, old_memory):

        dialog = ctk.CTkInputDialog(
            text="Edit memory:",
            title="Edit Memory"
        )

        new_memory = dialog.get_input()

        if new_memory is None:
            return

        new_memory = new_memory.strip()

        if not new_memory:
            return

        memories = load_memory()

        if index < len(memories):

            memories[index] = new_memory

            save_memory(memories)

            self.refresh_memories()

    def delete_memory(self, index):

        memories = load_memory()

        if index < len(memories):

            memories.pop(index)

            save_memory(memories)

            self.refresh_memories()

    def update_chats(self, chats, active_chat):

        for widget in self.chat_list.winfo_children():
            widget.destroy()

        for chat_id, chat_data in chats.items():

            row = ctk.CTkFrame(
                self.chat_list,
                fg_color="#292C3D" if chat_id == active_chat else "transparent",
                corner_radius=8
            )
            row.pack(fill="x", pady=3)

            chat_button = ctk.CTkButton(
                row,
                text=chat_data["title"],
                anchor="w",
                fg_color="transparent",
                hover_color="#383B52",
                command=lambda selected=chat_id:
                    self.select_chat_command(selected)
            )
            chat_button.pack(
                side="left",
                fill="x",
                expand=True,
                padx=(5, 0),
                pady=4
            )

            delete_button = ctk.CTkButton(
                row,
                text="X",
                width=30,
                fg_color="transparent",
                hover_color="#8B303D",
                command=lambda selected=chat_id:
                    self.delete_chat_command(selected)
            )
            delete_button.pack(
                side="right",
                padx=5,
                pady=4
            )
