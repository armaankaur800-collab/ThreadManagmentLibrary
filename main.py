import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time

class SchedulerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CPU Scheduler - Version 6")
        self.root.geometry("700x500")

        self.processes = []
        self.build_ui()

    def build_ui(self):
        title = tk.Label(self.root, text="CPU Scheduler (Version 6)", font=("Arial", 18))
        title.pack(pady=10)

        # Algorithm chooser
        algo_frame = tk.Frame(self.root)
        algo_frame.pack()

        tk.Label(algo_frame, text="Select Algorithm:", font=("Arial", 12)).grid(row=0, column=0)
        self.algo_choice = ttk.Combobox(
            algo_frame,
            values=["FCFS", "SJF", "Priority", "Round Robin"],
            state="readonly",
            width=20
        )
        self.algo_choice.grid(row=0, column=1)
        self.algo_choice.current(0)

        # Process input frame
        input_frame = tk.Frame(self.root)
        input_frame.pack(pady=10)

        tk.Label(input_frame, text="Process ID").grid(row=0, column=0)
        tk.Label(input_frame, text="Burst Time").grid(row=0, column=1)
        tk.Label(input_frame, text="Priority").grid(row=0, column=2)

        self.pid = tk.Entry(input_frame, width=10)
        self.burst = tk.Entry(input_frame, width=10)
        self.priority = tk.Entry(input_frame, width=10)

        self.pid.grid(row=1, column=0)
        self.burst.grid(row=1, column=1)
        self.priority.grid(row=1, column=2)

        add_btn = tk.Button(self.root, text="Add Process", command=self.add_process)
        add_btn.pack()

        self.output_box = tk.Text(self.root, height=12, width=80)
        self.output_box.pack(pady=10)

        start_btn = tk.Button(self.root, text="Start Scheduling", command=self.start_scheduling)
        start_btn.pack()

    def add_process(self):
        try:
            p = self.pid.get()
            b = int(self.burst.get())
            pr = int(self.priority.get() or 0)
            self.processes.append([p, b, pr])
            self.output_box.insert(tk.END, f"Added: {p} (BT={b}, PR={pr})\n")
        except ValueError:
            messagebox.showerror("Error", "Invalid input")

    def start_scheduling(self):
        if not self.processes:
            messagebox.showerror("Error", "Add processes first")
            return

        t = threading.Thread(target=self.run_scheduler)
        t.start()

    def log(self, msg):
        self.output_box.insert(tk.END, msg + "\n")
        self.output_box.see(tk.END)
        time.sleep(0.5)

    # Scheduler core
    def run_scheduler(self):
        algo = self.algo_choice.get()
        procs = [p[:] for p in self.processes]

        self.log(f"Running {algo} scheduling...")

        if algo == "FCFS":
            for p in procs:
                self.log(f"Running {p[0]} for {p[1]} ms")
        elif algo == "SJF":
            procs.sort(key=lambda x: x[1])
            for p in procs:
                self.log(f"SJF picked {p[0]} (BT={p[1]})")
        elif algo == "Priority":
            procs.sort(key=lambda x: x[2])
            for p in procs:
                self.log(f"Priority picked {p[0]} (PR={p[2]})")
        elif algo == "Round Robin":
            quantum = 4
            self.log(f"Quantum = {quantum}")
            q = procs[:]
            while q:
                p = q.pop(0)
                run = min(quantum, p[1])
                self.log(f"RR running {p[0]} for {run} ms")
                p[1] -= run
                if p[1] > 0:
                    q.append(p)

        self.log("Scheduling Complete.")

root = tk.Tk()
app = SchedulerGUI(root)
root.mainloop()