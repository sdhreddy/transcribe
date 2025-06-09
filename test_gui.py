#!/usr/bin/env python3
"""
Test if tkinter GUI can display in WSL
"""
import tkinter as tk
import sys

def test_tkinter():
    """Test basic tkinter functionality"""
    try:
        print("Creating tkinter window...")
        root = tk.Tk()
        root.title("WSL GUI Test")
        root.geometry("300x200")
        
        label = tk.Label(root, text="If you see this, GUI works!")
        label.pack(pady=50)
        
        button = tk.Button(root, text="Close", command=root.quit)
        button.pack()
        
        print("Window created, starting mainloop...")
        print("Note: Window should appear. Close it to continue.")
        
        # Use a timeout to avoid hanging
        root.after(5000, lambda: print("GUI timeout - if no window appeared, there's a display issue"))
        root.mainloop()
        
        print("Tkinter test completed successfully")
        return True
        
    except Exception as e:
        print(f"Tkinter test failed: {e}")
        return False

if __name__ == "__main__":
    test_tkinter()