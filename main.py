import tkinter as tk
from tkinter import ttk
import threading
import time
import queue

class MultiLevelCPU:
    def __init__(self):
        self.queues = {
            "High": queue.Queue(),
            "Medium": queue.Queue(),
            "Low": queue.Queue()
        }
        self.running = False
        self.timeline_log = []

    def add_task(self, name, burst, priority):
        self.queues[priority].put([name, burst])

    def get_next_task(self):
        for level in ["High", "Medium", "Low"]:
            if not self.queues[level].empty():
                return level, self.queues[level].get()
        return None, None

    def run(self, update_ui_callback):
        self.running = True
        while self.running:
            level, task = self.get_next_task()
            if task is None:
                time.sleep(0.2)
                continue

            name, burst = task
            for t in range(burst):
                if not self.running:
                    return
                update_ui_callback(name, level, t + 1, burst)
                time.sleep(0.25)

            self.timeline_log.append(f"{name} finished from {level} queue")

    def stop(self):
        self.running = False


class CPU_GUI:
    def __init__(self, root):
        self.cpu = MultiLevelCPU()
        self.root = root
        root.title("Version 7: Multi-Level CPU Scheduler")
        root.geometry("700x500")

        self.setup_ui()

    def setup_ui(self):
        frame = tk.Frame(self.root)
        frame.pack(pady=10)

        tk.Label(frame, text="Task Name").grid(row=0, column=0)
        tk.Label(frame, text="Burst Time").grid(row=0, column=1)
        tk.Label(frame, text="Priority").grid(row=0, column=2)

        self.name_entry = tk.Entry(frame)
        self.burst_entry = tk.Entry(frame)

        self.name_entry.grid(row=1, column=0)
        self.burst_entry.grid(row=1, column=1)

        self.priority = ttk.Combobox(frame, values=["High", "Medium", "Low"], width=10)
        self.priority.grid(row=1, column=2)
        self.priority.current(0)

        tk.Button(frame, text="Add Task", command=self.add_task).grid(row=1, column=3, padx=10)

        self.start_btn = tk.Button(self.root, text="Start CPU", command=self.start_cpu)
        self.start_btn.pack(pady=10)

        self.progress = ttk.Progressbar(self.root, length=500)
        self.progress.pack(pady=10)

        self.status = tk.Label(self.root, text="Waiting...", font=("Arial", 12))
        self.status.pack()

        self.timeline = tk.Listbox(self.root, height=10, width=80)
        self.timeline.pack(pady=10)

    def add_task(self):
        name = self.name_entry.get()
        burst = int(self.burst_entry.get())
        pr = self.priority.get()

        self.cpu.add_task(name, burst, pr)
        self.timeline.insert(tk.END, f"Added {name} [{burst}] to {pr}")

    def update_ui(self, name, level, current, total):
        self.status.config(text=f"Running {name} from {level} ({current}/{total})")
        self.progress["value"] = (current / total) * 100

    def start_cpu(self):
        self.start_btn.config(state="disabled")
        th = threading.Thread(target=self.cpu.run, args=(self.update_ui,))
        th.daemon = True
        th.start()


root = tk.Tk()
app = CPU_GUI(root)
root.mainloop()