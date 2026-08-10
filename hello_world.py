import time
start_time = time.perf_counter()
import os
import tkinter as tk

root = tk.Tk()
root.title("RGB Triangle")
root.title("Triangle-python")
print(f"Process ID (PID) in Task Manager: {os.getpid()}")
 
canvas = tk.Canvas(root, width=400, height=400, bg="white")
canvas.pack()

r, g, b = 255, 128, 0  

# Use a formatted string to convert to a hex color string
rgb_color = f"#{r:02x}{g:02x}{b:02x}"

# Apply the color to the fill argument
#canvas.create_polygon(200, 50, 50, 350, 350, 350, fill=rgb_color)

for i in range(10000000):
    # Offset each triangle slightly so they don't stack directly on top of each other
    offset = i * 5
    canvas.create_polygon(
        200 + offset,
        50,
        50 + offset,
        350,
        350 + offset,
        350,
        fill="red",
        outline="black",
    )

end_time = time.perf_counter()
execution_time = end_time - start_time
print(f"{execution_time * 1000:.4f} ms")

# Open the file in append mode
with open("output.txt", "a") as file:
    file.write(f"\n{execution_time * 1000:.4f}")

root.mainloop()
