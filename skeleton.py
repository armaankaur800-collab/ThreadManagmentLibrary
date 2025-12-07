# v3_skeleton.py
# GUI skeleton for Version 3 (no threadpool logic yet)
import tkinter as tk
from tkinter import scrolledtext, messagebox

class V3Skeleton:
    def __init__(self, root):
        self.root = root
        root.title("ThreadPool GUI — Version 3 (Design Prototype)")
        root.geometry("800x600")

        # Left control panel
        self.left = tk.Frame(root, width=280, bg="#f0f0f0")
        self.left.pack(side="left", fill="y", padx=10, pady=10)

        tk.Label(self.left, text="ThreadPool Controller", font=("Arial", 14, "bold"), bg="#f0f0f0")\
            .pack(pady=(6,12))

        tk.Label(self.left, text="Threads:", bg="#f0f0f0").pack(anchor="w", padx=10)
        self.thread_entry = tk.Entry(self.left, width=10)
        self.thread_entry.insert(0, "4")
        self.thread_entry.pack(padx=10, pady=6)

        self.create_btn = tk.Button(self.left, text="Create Pool", width=20, bg="#4CAF50", fg="white",
                                    command=self.create_pool)
        self.create_btn.pack(padx=10, pady=6)

        self.add_btn = tk.Button(self.left, text="Add Task", width=20, bg="#2196F3", fg="white",
                                 command=self.add_task, state="disabled")
        self.add_btn.pack(padx=10, pady=6)

        self.shutdown_btn = tk.Button(self.left, text="Shutdown", width=20, bg="#f44336", fg="white",
                                      command=self.shutdown_pool, state="disabled")
        self.shutdown_btn.pack(padx=10, pady=6)

        # Status labels
        self.status_pool = tk.Label(self.left, text="Pool Status: Not created", bg="#f0f0f0")
        self.status_pool.pack(padx=10, pady=(20,2))
        self.status_workers = tk.Label(self.left, text="Workers: 0", bg="#f0f0f0")
        self.status_workers.pack(padx=10, pady=2)
        self.status_queued = tk.Label(self.left, text="Queued: 0", bg="#f0f0f0")
        self.status_queued.pack(padx=10, pady=2)

        # Right panel: queue visualization and log
        self.right = tk.Frame(root, bg="#ffffff")
        self.right.pack(side="right", expand=True, fill="both", padx=10, pady=10)

        tk.Label(self.right, text="Task Queue (visual):", font=("Arial", 12)).pack(anchor="nw")
        self.canvas = tk.Canvas(self.right, height=80, bg="#ffffff", highlightthickness=1, highlightbackground="#ddd")
        self.canvas.pack(fill="x", pady=(6,12))

        tk.Label(self.right, text="Live Log:", font=("Arial", 12)).pack(anchor="nw")
        self.log = scrolledtext.ScrolledText(self.right, state="disabled", height=20)
        self.log.pack(fill="both", expand=True, pady=(6,0))

        # Skeleton state (no real pool)
        self.pool_created = False
        self.task_id_counter = 0
        self.visual_items = []  # for queued task rectangles

    # Button handlers (stubs)
    def create_pool(self):
        if self.pool_created:
            messagebox.showinfo("Info", "Pool already created")
            return
        try:
            k = int(self.thread_entry.get())
            if k <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Enter a valid positive integer for threads")
            return

        # Enable buttons (actual pool creation will replace this)
        self.pool_created = True
        self.status_pool.config(text=f"Pool Status: Running")
        self.status_workers.config(text=f"Workers: {k}")
        self.add_btn.config(state="normal")
        self.shutdown_btn.config(state="normal")
        self.log_message(f"Pool created with {k} workers (skeleton)")

    def add_task(self):
        if not self.pool_created:
            messagebox.showwarning("Warning", "Create pool first")
            return
        self.task_id_counter += 1
        tid = self.task_id_counter
        # Add visual rectangle for queued task
        x = 10 + len(self.visual_items) * 60
        rect = self.canvas.create_rectangle(x, 10, x+50, 60, fill="#ffd966")
        txt = self.canvas.create_text(x+25, 35, text=str(tid))
        self.visual_items.append((rect, txt))
        self.status_queued.config(text=f"Queued: {len(self.visual_items)}")
        self.log_message(f"Task {tid} queued (skeleton)")
        # NOTE: worker execution logic to remove rectangles will be implemented later

    def shutdown_pool(self):
        if not self.pool_created:
            return
        self.pool_created = False
        self.status_pool.config(text="Pool Status: Not created")
        self.status_workers.config(text="Workers: 0")
        self.add_btn.config(state="disabled")
        self.shutdown_btn.config(state="disabled")
        self.canvas.delete("all")
        self.visual_items.clear()
        self.status_queued.config(text="Queued: 0")
        self.log_message("Pool shutdown (skeleton)")

    def log_message(self, s):
        self.log.config(state="normal")
        self.log.insert("end", s + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

if __name__ == "__main__":
    root = tk.Tk()
    app = V3Skeleton(root)
    root.mainloop()