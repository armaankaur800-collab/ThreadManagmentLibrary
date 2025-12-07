import threading
from queue import Queue
import time
import tkinter as tk
from tkinter import messagebox

# ================================
#   ThreadPool (Same Logic)
# ================================

class ThreadPool:
    def __init__(self, num_threads):
        self.tasks = Queue()
        self.stop = False
        self.workers = []
        self.task_count = 0
        self.lock = threading.Lock()

        for i in range(num_threads):
            t = threading.Thread(target=self.worker, daemon=True)
            t.start()
            self.workers.append(t)

    def worker(self):
        while not self.stop:
            task = self.tasks.get()
            if task is None:
                break
            task()
            with self.lock:
                self.task_count -= 1
            self.tasks.task_done()

    def add_task(self, func):
        with self.lock:
            self.task_count += 1
        self.tasks.put(func)

    def shutdown(self):
        self.stop = True
        for _ in self.workers:
            self.tasks.put(None)
        for t in self.workers:
            t.join()


# ================================
#             GUI
# ================================

class GUI:
    def __init__(self, pool):
        self.pool = pool

        self.window = tk.Tk()
        self.window.title("Thread Manager - Version 2 GUI")
        self.window.geometry("420x350")
        self.window.configure(bg="#1e1e1e")

        # ---------- Title ----------
        title = tk.Label(self.window, text="Thread Management Dashboard",
                         font=("Arial", 16, "bold"), fg="white", bg="#1e1e1e")
        title.pack(pady=15)

        # ---------- Task Counter ----------
        self.task_label = tk.Label(self.window, text="Tasks in queue: 0",
                                   font=("Arial", 14), fg="#00FFAA", bg="#1e1e1e")
        self.task_label.pack(pady=5)

        # ---------- Active Threads ----------
        self.thread_label = tk.Label(self.window, text="Active threads: 0",
                                     font=("Arial", 14), fg="#00D0FF", bg="#1e1e1e")
        self.thread_label.pack(pady=5)

        # ---------- Add Task Button ----------
        self.add_btn = tk.Button(self.window, text="Add Task",
                                 font=("Arial", 14), bg="#4CAF50",
                                 fg="white", width=15, command=self.add_task)
        self.add_btn.pack(pady=20)

        # Auto update labels every 500ms
        self.update_gui()

        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

    # Add new task
    def add_task(self):
        self.pool.add_task(lambda: time.sleep(1))
        messagebox.showinfo("Task Added", "Your task has been added to the queue!")

    # Live update GUI
    def update_gui(self):
        self.task_label.config(text=f"Tasks in queue: {self.pool.task_count}")
        self.thread_label.config(text=f"Active threads: {len(self.pool.workers)}")

        self.window.after(500, self.update_gui)

    # Safe shutdown
    def on_close(self):
        self.pool.shutdown()
        self.window.destroy()

    def run(self):
        self.window.mainloop()


# ================================
#           MAIN
# ================================

if __name__ == "__main__":
    pool = ThreadPool(4)   # 4 worker threads
    gui = GUI(pool)
    gui.run()