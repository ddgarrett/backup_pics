import tkinter as tk
from tkinter import messagebox

# Define the functions to be executed
def function_a():
    messagebox.showinfo("Function A", "Executing Function A!")

def function_b():
    messagebox.showinfo("Function B", "Executing Function B!")

def function_c():
    messagebox.showinfo("Function C", "Executing Function C!")

# Create a lookup table (dictionary) mapping function names to functions
function_lookup = {
    "Function A": function_a,
    "Function B": function_b,
    "Function C": function_c,
}

def run_selected_function():
    """Retrieves the selected function from the Listbox and executes it."""
    selected_index = listbox.curselection()
    if selected_index:
        selected_function_name = listbox.get(selected_index[0])
        function_to_run = function_lookup.get(selected_function_name)
        if function_to_run:
            function_to_run()
        else:
            messagebox.showerror("Error", f"Function '{selected_function_name}' not found in lookup table.")
    else:
        messagebox.showwarning("Selection Error", "Please select a function to run.")

# Create the main application window
root = tk.Tk()
root.title("Function Selector")

# Create a Listbox to display the function names
listbox = tk.Listbox(root, selectmode=tk.SINGLE)
for name in function_lookup.keys():
    listbox.insert(tk.END, name)
listbox.pack(pady=10)

# Create a button to run the selected function
run_button = tk.Button(root, text="Run Selected Function", command=run_selected_function)
run_button.pack(pady=5)

# Start the Tkinter event loop
root.mainloop()