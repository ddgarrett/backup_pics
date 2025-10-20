import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

'''
python 3.11 TKinter program to display a list of functions and allow you to select one of the functions to run. 
Each function would have a lookup table that defines the python program to run for a given function.
Give the TKinter UI a modern look and feel. 
Include a visible list of all available functions and execute the function when an item in the list is clicked.

Prereq: pip install ttkbootstrap

'''



def function_one():
    """A sample function to demonstrate execution."""
    messagebox.showinfo("Function One", "Hello from Function One!")

def function_two():
    """Another sample function to demonstrate execution."""
    messagebox.showinfo("Function Two", "Hello from Function Two!")

def function_three():
    """A third sample function to demonstrate execution."""
    messagebox.showinfo("Function Three", "Hello from Function Three!")

# The lookup table that defines the function names and the programs to run.
FUNCTION_LOOKUP_TABLE = {
    "Function 1: Display message": function_one,
    "Function 2: Show another message": function_two,
    "Function 3: Third function call": function_three,
}

class FunctionRunnerApp(ttk.Window):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("Modern Tkinter Function Runner")
        self.geometry("450x300")
        
        # Configure a modern-looking window using ttkbootstrap themes.
        self.style.theme_use("superhero") # You can try other themes like "cosmo" or "flatly".

        self.create_widgets()
    
    def create_widgets(self):
        """Creates and places all the widgets in the GUI."""
        frame = ttk.Frame(self, padding=15)
        frame.pack(fill=BOTH, expand=True)

        ttk.Label(frame, text="Select a function to run:", font=("Helvetica", 14, "bold")).pack(pady=(0, 10))

        # Create a Treeview widget to display the list of functions.
        # This provides a more modern and structured list than the basic Listbox.
        self.tree = ttk.Treeview(frame, columns=("function_name"), show="headings")
        self.tree.heading("function_name", text="Available Functions")
        self.tree.pack(fill=BOTH, expand=True)
        
        # Populate the Treeview with function names from the lookup table.
        for name in FUNCTION_LOOKUP_TABLE.keys():
            self.tree.insert("", END, values=(name,))
            
        # Bind a click event to the Treeview to trigger the function execution.
        self.tree.bind("<<TreeviewSelect>>", self.on_function_select)
        
    def on_function_select(self, event):
        """Executes the selected function when a list item is clicked."""
        selected_item = self.tree.focus()
        if not selected_item:
            return

        # Get the selected function name from the Treeview item.
        selected_function_name = self.tree.item(selected_item, "values")[0]
        
        # Look up the function in the dictionary and run it.
        if selected_function_name in FUNCTION_LOOKUP_TABLE:
            function_to_run = FUNCTION_LOOKUP_TABLE[selected_function_name]
            function_to_run()

if __name__ == "__main__":
    app = FunctionRunnerApp()
    app.mainloop()
