from rich.console import Console
from dataclasses import dataclass
from random import choice
from sqlite3 import Error, connect
from prompt_toolkit import PromptSession
import os

cons = Console()

# Todo
@dataclass
class Todo:
    tag: str
    content: str
    done: bool

# Main
class Main:
    def __init__(self) -> None:
        self.todos: list[Todo] = [] # Todos
        self.tags: dict[str, str] = {} # Tags
        self.colors: list[str] = ["red", "green", "yellow", "blue", "magenta", "cyan"] # List of colors
        self.db_file = "uluto.db" # Default database filename
        self.has_changed = False # Check for changes

        # Argument required for each command
        self.cmd_argument_required = {
            "add_todo": 0,
            "add_tag": 2,
            "mark": 1,
            "delete": 1,
            "clear": 1,
            "change_tag_color": 0,
            "clearscr": 0,
            "help": 0,
        }

        # Command names
        self.cmds = ["add_todo", "add_tag", "mark", "delete", "clear", "change_tag_color", "clearscr", "help"]

        self.cmd_map = {
            "add_todo": lambda: self.add_todo(),
            "mark": lambda idx: self.mark_as_done(idx),
            "delete": lambda idx: self.delete(idx),
            "clear": lambda todo_type: self.clear(todo_type),
            "change_tag_color": lambda name: self.change_tag_color(name),
            "help": lambda: self.print_help(),
        }

        self.version = "0.1"
        self.greeting = f"""
[red]ULuto[/red] - Ultimate Luto, version [default]{self.version}[/default].
Type 'help' for help, and 'exit' to quit.
        """

        self.help = """
    add_todo: Add a new todo
    add_tag <name> <color>: Add a new tag
    mark <position of todo from 0>: Mark a todo as done
    delete <all | position of todo from 0>: Delete a specific todo
    clear <done | all>: Clear finished todos or all todos
    change_tag_color <tag_name>: Change color of a tag
    save <db_name?>: Save the todos into the database
    load <db_name?>: Load information to the todo list from the database
    help: Print this help message
    exit: Exit this program
        """

        self.prompt = ">> "

    # Render the todos
    def render(self) -> None:
        if len(self.todos) == 0:
             print("You have no todo right now.")
        else:
             for todo in self.todos:
                 tag_color = self.tags[todo.tag]
                 cons.print(f"[{tag_color}]{todo.tag}[/{tag_color}]: {todo.content} [green]{'Done!' if todo.done else ''}[/green]")

    # Ask for color
    def ask_for_color(self, custom_prompt: str = "") -> str:
        color = ""

        while True:
            color = input(f"{custom_prompt if len(custom_prompt) != 0 else 'Color'} (? for more information): ")

            if color == "?":
                print("Avaliable colors: ")
                for color in self.colors:
                    cons.print(f"[{color}]{color}[/{color}]")
                print("random")
            elif color == "random":
                color = choice(self.colors)
                break
            elif color not in self.colors:
                print(f"{color} is not a valid color.")
            else:
                break

        return color

    # Add a todo
    def add_todo(self) -> None:
        tag = input("Tag: ")
        content = input("Content: ")

        if tag not in self.tags:
            while True:
                choice = self.yes_no_choice(f"Tag '{tag}' hasn't been created yet. Create tag?")

                if choice:
                    self.add_tag(name=tag, color=self.ask_for_color(custom_prompt="Tag color"))
                break

        self.todos.append(Todo(tag, content, False))
        print("Todo added successfully.")
        self.has_changed = True

    # Add a tag
    def add_tag(self, name: str, color: str) -> None:
        self.tags[name] = color
        print(f"New tag '{name}' added successfully.")
        self.has_changed = True

    # Mark a specific todo or all todos
    def mark_as_done(self, idx: str) -> None:
        try:
            if idx == "all":
                for indx in range(len(self.todos)):
                    self.todos[indx].done = not self.todos[indx].done
            else:
                self.todos[int(idx)].done = not self.todos[int(idx)].done
        except Exception as e:
            print(f"Error: {e}")

    # Delete a specific todo
    def delete(self, idx: int) -> None:
        try:
            del self.todos[idx]
            print("Todo deleted successfully.")
        except Exception as e:
            print(f"Error: {e}")

    # Clear finished todos or all todos
    def clear(self, todo_type: str) -> None:
        if todo_type == "done":
            [self.todos.pop(idx) for idx in range(len(self.todos) - 1) if self.todos[idx].done]
        elif todo_type == "all":
            self.todos = []
        else:
            print(f"'{todo_type}' is not 'done' or 'all'.")

    # Change tag color
    def change_tag_color(self, tag: str) -> None:
        self.tags[tag] = self.ask_for_color(custom_prompt="New tag color")
        print("Tag color changed successfully.")

    # Save to database
    def save(self, file: str) -> None:
        try:
            # If the database does exist and it is not empty...
            if os.path.exists(file) and os.stat(file).st_size != 0:
                while True:
                    # ... we will ask if the user want to overwrite it or not
                    final_choice = self.yes_no_choice("This database has been written before. Overwrite?")
                    if not final_choice: raise Error("Please ignore this error.")
                    os.remove(file)
                    break
            conn = connect(file)
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS todos(tag text, content text, done bool);")
            cursor.execute("CREATE TABLE IF NOT EXISTS tags(name text, color text);")

            for todo in self.todos:
                cursor.execute("INSERT INTO todos VALUES(?, ?, ?);", (todo.tag, todo.content, todo.done))

            for tag in self.tags:
                cursor.execute("INSERT INTO tags VALUES(?, ?)", (tag, self.tags[tag]))

            conn.commit()

            self.close_conn_and_print("Save to database successfully.", conn, False)
        except Error as e:
            print(f'Error when saving database: {e}')

    # Load the database
    def load(self, file: str) -> None:
        try:
            conn = connect(file)
            cursor = conn.cursor()

            # Fetch all todos and tags from the DB
            db_todos = cursor.execute("SELECT * FROM todos;").fetchall()
            db_tags = cursor.execute("SELECT * FROM tags;").fetchall()

            # Clear todos and tags before we go
            self.clear("all")
            self.tags = {}

            for todo in db_todos:
                done = todo[2]
                # SQLite (and perhaps other SQL DBs) uses 0 and 1 to indicate
                # False and True. In here, we check if done == 1 (done == True)
                done = done == 1
                self.todos.append(Todo(todo[0], todo[1], done))

            for tag in db_tags:
                # Create key (tag name) - value (tag color) assignment
                self.tags[tag[0]] = tag[1]

            self.close_conn_and_print("Load from database successfully.", conn, True)
        except Error as e:
            print(f'Error when loading database: {e}')

    # Generated by Sourcery. Renamed from "_extracted_from_load_23"
    def close_conn_and_print(self, msg, conn, has_changed):
        print(msg)
        conn.close()
        self.has_changed = has_changed

    def print_help(self) -> None:
        cons.print("[bold]Commands: [/bold]", end="")
        print(self.help)

    # Do a yes-no question
    def yes_no_choice(self, qs: str) -> bool:
        while True:
            final_choice = input(f"{qs} (y/n) ").lower()

            # if final_choice is not empty
            if final_choice:
                return (True if final_choice == "y" else False)
            else:
                print("Please choose yes (y) or no (n)")

    def run(self) -> None:
        cons.print(self.greeting)
        session = PromptSession()

        while True:
            self.render()
            inpt = session.prompt(self.prompt).strip().split()

            # if input is not empty
            if inpt:
                cmd = inpt[0]

                if cmd in self.cmds:
                    if self.cmd_argument_required[cmd] != len(inpt) - 1:
                        print(f"Error: expected {self.cmd_argument_required[cmd]} argument(s), got {len(inpt) - 1}")
                    elif cmd == "add_tag":
                        self.add_tag(inpt[1], inpt[2])
                    else:
                        if len(inpt) > 1:
                            self.cmd_map[cmd](inpt[1])
                        else:
                            self.cmd_map[cmd]()
                        self.has_changed = True
                elif cmd == "exit":
                    if self.has_changed:
                        the_choice = self.yes_no_choice("You haven't save your todo yet. Save?")
                        if the_choice:
                            self.save(self.db_file)
                    break
                elif cmd == "load":
                    self.load(inpt[1] if len(inpt) > 1 else self.db_file)
                elif cmd == "save":
                    self.save(inpt[1] if len(inpt) > 1 else self.db_file)
                else:
                    print(f"{cmd}: Invalid command.")

if __name__ == "__main__":
    Main().run()
