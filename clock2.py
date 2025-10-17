import tkinter as tk
import tkinter.font as tkFont
import time

'''
  Generate a python program that uses tkinter on a raspberry pi 5 to display a 24 hour clock. 
  The font should automatically resize if the window is resized. 
'''

class ClockApp:
    """
    A simple Tkinter application to display a 24-hour clock
    with a font that resizes automatically with the window.
    """
    def __init__(self, root):
        self.root = root
        self.root.title("RPi5 Clock")
        # Set an initial size for the window
        self.root.geometry("700x250")
        self.root.configure(bg='black')

        # Use a tk.Font object to easily reconfigure the font size later
        self.clock_font = tkFont.Font(family="DS-Digital", size=10, weight="bold")

        # Create the label that will display the time
        self.time_label = tk.Label(
            self.root,
            font=self.clock_font,
            bg="black",
            fg="#39FF14"  # A bright, digital-style green
        )
        # Make the label expand to fill the entire window
        self.time_label.pack(fill='both', expand=True)

        # Bind the window's resize event (<Configure>) to the resize_font method
        self.root.bind("<Configure>", self.resize_font)

        # Start the clock update loop
        self.update_clock()

    def update_clock(self):
        """
        Fetches the current time, formats it, and updates the label.
        Schedules itself to run again after 1000ms (1 second).
        """
        # Format the time as HH:MM:SS in 24-hour format
        current_time = time.strftime('%H:%M')
        self.time_label.config(text=current_time)
        
        # Schedule the next update
        self.root.after(60000, self.update_clock)

    def resize_font(self, event):
        """
        Calculates and applies a new font size based on the window's height.
        This method is called automatically whenever the window is resized.
        """
        # The 'event' object contains the new dimensions of the window
        window_height = event.height
        
        # Calculate a new font size. We use a fraction of the window's height.
        # The factor (e.g., 2.5) can be adjusted to change how large the font is.
        # We ensure the font size is at least 8.
        new_font_size = max(8, int(window_height / 2.5))
        
        # Apply the new size to our font object
        self.clock_font.config(size=new_font_size)


if __name__ == "__main__":
    # Standard Tkinter setup
    root = tk.Tk()
    app = ClockApp(root)
    root.mainloop()
