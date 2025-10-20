import tkinter as tk
from tkinter import ttk, messagebox
import sv_ttk

'''
python 3.11 TKinter program to display a list of functions and allow you to select one of the functions to run. 
Each function would have a lookup table that defines the python program to run for a given function.
Give the TKinter UI a modern look and feel. 
Include a visible list of all available functions and execute the function when an item in the list is clicked.

Prereq: pip install sv-ttk

'''


# --- Function Definitions ---
# Each function to be run needs to be defined here.
# You can add more functions as needed.
def say_hello():
    response = messagebox.askokcancel("Connect Device", "Connect Pixel Phone, press OK to continue")
    print("message hello box closed, response:", response)

def show_message():
    messagebox.showinfo("Function Executed", "This is a custom message from function 2.")

def display_info():
    messagebox.showinfo("Function Executed", "Function 3: Here is some important information.")

def run_task():
    messagebox.showinfo("Function Executed", "Running a generic task for function 4.")


# --- Lookup Table (Dictionary) ---
# This dictionary maps the function number and name to the actual function reference.
# The keys are used to populate the listbox and can be used for direct access.
function_lookup = {
    1: {"name": "Say Hello", "function": say_hello},
    2: {"name": "Show a Message", "function": show_message},
    3: {"name": "Display Information", "function": display_info},
    4: {"name": "Run a Task", "function": run_task}
}

class FunctionRunnerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Function Runner")
        self.geometry("500x400")

        # Set the modern theme from sv-ttk
        sv_ttk.set_theme("light")

        # Create the main frame with padding
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill="both", expand=True)

        # Title Label
        title_label = ttk.Label(
            main_frame,
            text="Select a function to run",
            font=("Helvetica", 16, "bold")
        )
        title_label.pack(pady=(0, 20))

        # --- Function Listbox ---
        list_label = ttk.Label(main_frame, text="Available Functions:")
        list_label.pack(anchor="w")

        listbox_frame = ttk.Frame(main_frame)
        listbox_frame.pack(fill="both", expand=True, pady=(5, 10))

        self.function_listbox = tk.Listbox(listbox_frame, height=10, font=("Helvetica", 12))
        self.function_listbox.pack(side="left", fill="both", expand=True)

        # Populate the listbox with function names
        self.populate_listbox()

        # Add a scrollbar
        scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", command=self.function_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.function_listbox.config(yscrollcommand=scrollbar.set)

        # Bind listbox selection event to the handler
        self.function_listbox.bind("<<ListboxSelect>>", self.on_listbox_select)

        # --- Entry for Typing Function Number ---
        entry_frame = ttk.Frame(main_frame)
        entry_frame.pack(fill="x", pady=10)

        entry_label = ttk.Label(entry_frame, text="Type function number and press Enter:")
        entry_label.pack(side="left", padx=(0, 10))

        self.function_entry = ttk.Entry(entry_frame, width=5)
        self.function_entry.pack(side="left")

        # Bind the Enter key to the entry widget
        self.function_entry.bind("<Return>", self.on_entry_enter)

        # --- Run Button ---
        run_button = ttk.Button(
            main_frame,
            text="Run Selected Function",
            command=self.run_function_from_listbox,
            style="Accent.TButton"  # Use a theme-specific accent style
        )
        run_button.pack(pady=10)

        # Add a status bar
        self.status_label = ttk.Label(main_frame, text="Ready.", relief="groove")
        self.status_label.pack(side="bottom", fill="x", pady=(10, 0))

    def populate_listbox(self):
        """Populates the listbox with function names from the lookup table."""
        for num, func_data in function_lookup.items():
            self.function_listbox.insert(tk.END, f"{num}. {func_data['name']}")

    def run_function(self, function_number):
        """Executes the function from the lookup table based on the number."""
        try:
            func_data = function_lookup[function_number]
            self.update_status(f"Executing: {func_data['name']}...")
            self.after(100, lambda: func_data['function']())
            self.update_status(f"Execution complete for: {func_data['name']}")
        except KeyError:
            messagebox.showerror("Error", f"Function number {function_number} not found.")
            self.update_status("Error: Invalid function number.")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")
            self.update_status("Error during execution.")

    def on_listbox_select(self, event):
        """Handler for listbox selection."""
        try:
            selected_index = self.function_listbox.curselection()[0]
            function_number = selected_index + 1
            self.run_function(function_number)
        except IndexError:
            # Handle case where selection is cleared
            pass

    def on_entry_enter(self, event):
        """Handler for Enter key press in the entry widget."""
        try:
            function_number = int(self.function_entry.get())
            self.run_function(function_number)
            self.function_entry.delete(0, tk.END)  # Clear entry box
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number.")
            self.update_status("Error: Invalid input.")

    def run_function_from_listbox(self):
        """Handler for the 'Run Selected Function' button."""
        try:
            selected_index = self.function_listbox.curselection()[0]
            function_number = selected_index + 1
            self.run_function(function_number)
        except IndexError:
            messagebox.showwarning("Warning", "Please select a function from the list first.")

    def update_status(self, message):
        """Updates the status bar with a given message."""
        self.status_label.config(text=message)
        self.update_idletasks()

if __name__ == "__main__":
    app = FunctionRunnerApp()
    app.mainloop()
