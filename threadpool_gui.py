# """
# v4_threadpool_gui.py
# Version 4: Tkinter GUI + ThreadPool + realtime timestamped log + queue visualization.

# Run:
#     python v4_threadpool_gui.py

# Features:
# - Enter thread count and Create Pool
# - Add Task button (tasks simulate work and post logs)
# - Shutdown button (graceful)
# - Scrollable log showing timestamped messages from workers
# - Visual queue: queued task boxes appear, removed when taken by worker
# - Safe GUI updates using gui_queue polled by main thread
# """

import threading
from queue import Queue, Empty
import time
import tkinter as tk
from tkinter import scrolledtext, messagebox
from datetime import datetime
import random

# ------------------------------
# ThreadPool implementation
# ------------------------------
class ThreadPool:
    def __init__(self):
        # tasks queue (callables)
        self.tasks = Queue()
        self.workers = []
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.next_task_id = 1  # local counter if needed

    def create(self, n, gui_queue=None):
        """Create n worker threads. If a pool already exists, does nothing."""
        if self.workers:
            return
        self.stop_event.clear()
        for i in range(n):
            t = threading.Thread(target=self._worker_loop, args=(i, gui_queue), daemon=True)
            t.start()
            self.workers.append(t)

    def _worker_loop(self, worker_index, gui_queue):
        """Worker thread: waits for tasks and executes them."""
        while not self.stop_event.is_set():
            try:
                task_info = self.tasks.get(timeout=0.2)  # blocks briefly for new tasks
            except Empty:
                continue
            if task_info is None:
                # shutdown sentinel
                self.tasks.task_done()
                break
            task_id, task_callable = task_info
            # Notify GUI: task started
            if gui_queue:
                gui_queue.put(("log", timestamp(), f"Task {task_id} started on worker {worker_index}"))
                gui_queue.put(("task_started", task_id))
            try:
                task_callable()  # run task
            except Exception as e:
                if gui_queue:
                    gui_queue.put(("log", timestamp(), f"Task {task_id} raised exception: {e}"))
            # Notify GUI: task finished
            if gui_queue:
                gui_queue.put(("log", timestamp(), f"Task {task_id} finished on worker {worker_index}"))
                gui_queue.put(("task_finished", task_id))
            self.tasks.task_done()

    def submit(self, task_callable):
        """Submit a callable as a task. Returns an assigned task id."""
        with self.lock:
            tid = self.next_task_id
            self.next_task_id += 1
        self.tasks.put((tid, task_callable))
        return tid

    def shutdown(self):
        """Graceful shutdown: signal threads to stop and join them."""
        self.stop_event.set()
        # push sentinel None for each worker to ensure they exit quickly
        for _ in self.workers:
            self.tasks.put(None)
        for t in self.workers:
            t.join()
        self.workers = []


# ------------------------------
# Helper functions
# ------------------------------
def timestamp():
    """Return current time string for logs."""
    return datetime.now().strftime("%H:%M:%S")

# Sample task factory: simulates work for a given duration
def make_sample_task(duration_ms=700):
    def task():
        # simulate CPU or IO work
        time.sleep(duration_ms / 1000.0)
    return task

# ------------------------------
# GUI Application
# ------------------------------
class ThreadPoolGUI:
    def __init__(self, root):
        self.root = root
        root.title("ThreadPool Visualizer - Version 4")
        root.geometry("900x600")
        self.gui_queue = Queue()  # thread-safe queue for GUI updates from workers

        # ThreadPool object (created on Create Pool)
        self.pool = ThreadPool()

        # Visual state tracking
        self.queued_visuals = {}   # task_id -> (rect_id, text_id)
        self.visual_order = []     # ordered list of task_ids for queue display
        self.max_visual_slots = 12 # for horizontal display
        self.task_count = 0

        # Left control panel
        self.left = tk.Frame(root, width=300, bg="#f5f5f5")
        self.left.pack(side="left", fill="y", padx=8, pady=8)

        tk.Label(self.left, text="ThreadPool Controller", font=("Helvetica", 14, "bold"), bg="#f5f5f5").pack(pady=(6,12))

        tk.Label(self.left, text="Threads:", bg="#f5f5f5").pack(anchor="w", padx=12)
        self.thread_entry = tk.Entry(self.left, width=10)
        self.thread_entry.insert(0, "4")
        self.thread_entry.pack(padx=12, pady=6)

        self.create_btn = tk.Button(self.left, text="Create Pool", bg="#2ecc71", fg="white", width=20, command=self.create_pool)
        self.create_btn.pack(padx=12, pady=6)

        self.add_btn = tk.Button(self.left, text="Add Task", bg="#3498db", fg="white", width=20, command=self.add_task, state="disabled")
        self.add_btn.pack(padx=12, pady=6)

        self.shutdown_btn = tk.Button(self.left, text="Shutdown", bg="#e74c3c", fg="white", width=20, command=self.shutdown_pool, state="disabled")
        self.shutdown_btn.pack(padx=12, pady=6)

        # task duration slider
        tk.Label(self.left, text="Task duration (ms):", bg="#f5f5f5").pack(anchor="w", padx=12, pady=(12,0))
        self.duration_scale = tk.Scale(self.left, from_=100, to=3000, orient="horizontal", length=200, bg="#f5f5f5")
        self.duration_scale.set(700)
        self.duration_scale.pack(padx=12, pady=(0,12))

        # status labels
        self.status_pool = tk.Label(self.left, text="Pool Status: Not created", bg="#f5f5f5")
        self.status_pool.pack(padx=12, pady=(8,4))
        self.status_workers = tk.Label(self.left, text="Workers: 0", bg="#f5f5f5")
        self.status_workers.pack(padx=12, pady=2)
        self.status_queued = tk.Label(self.left, text="Queued: 0", bg="#f5f5f5")
        self.status_queued.pack(padx=12, pady=2)

        # Right panel for visuals and logs
        self.right = tk.Frame(root, bg="#ffffff")
        self.right.pack(side="right", expand=True, fill="both", padx=8, pady=8)

        # Queue visualization (canvas)
        tk.Label(self.right, text="Task Queue (visual):", font=("Helvetica",12), bg="#ffffff").pack(anchor="nw", padx=10, pady=(6,0))
        self.canvas = tk.Canvas(self.right, height=100, bg="#ffffff", highlightthickness=1, highlightbackground="#ddd")
        self.canvas.pack(fill="x", padx=10, pady=(4,8))

        # Worker indicator strip (small rectangles showing busy/idle)
        tk.Label(self.right, text="Workers:", font=("Helvetica",12), bg="#ffffff").pack(anchor="nw", padx=10)
        self.worker_frame = tk.Frame(self.right, bg="#ffffff")
        self.worker_frame.pack(anchor="nw", padx=10, pady=(4,8))
        self.worker_indicators = []  # list of (canvas, rect_id)

        # Scrollable log
        tk.Label(self.right, text="Live Log (timestamped):", font=("Helvetica",12), bg="#ffffff").pack(anchor="nw", padx=10)
        self.log = scrolledtext.ScrolledText(self.right, state="disabled", height=18)
        self.log.pack(fill="both", expand=True, padx=10, pady=(4,10))

        # start polling gui_queue
        self.root.after(150, self.process_gui_queue)

        # handle close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ----------------------
    # GUI ↔ ThreadPool wiring
    # ----------------------
    def create_pool(self):
        if self.pool.workers:
            messagebox.showinfo("Info", "Pool already created")
            return
        try:
            k = int(self.thread_entry.get())
            if k <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Enter a valid positive integer for threads")
            return

        # create worker indicators
        self._setup_worker_indicators(k)

        # create pool and supply gui_queue for callbacks
        self.pool.create(k, gui_queue=self.gui_queue)

        self.create_btn.config(state="disabled")
        self.add_btn.config(state="normal")
        self.shutdown_btn.config(state="normal")
        self.status_pool.config(text="Pool Status: Running")
        self.status_workers.config(text=f"Workers: {k}")
        self.log_message(f"{timestamp()} - Pool created with {k} workers")

    def add_task(self):
        # create a task that will sleep for chosen ms and do nothing else
        dur = self.duration_scale.get()
        tid = self.pool.submit(make_sample_task(dur))
        self.task_count += 1
        # visual: add rectangle for queued task
        self._append_queue_visual(tid)
        self.status_queued.config(text=f"Queued: {len(self.visual_order)}")
        self.log_message(f"{timestamp()} - Task {tid} queued (duration {dur} ms)")

    def shutdown_pool(self):
        if not self.pool.workers:
            return
        self.pool.shutdown()
        self.log_message(f"{timestamp()} - Pool shutdown initiated")
        # reset UI state
        self.create_btn.config(state="normal")
        self.add_btn.config(state="disabled")
        self.shutdown_btn.config(state="disabled")
        self.status_pool.config(text="Pool Status: Not created")
        self.status_workers.config(text="Workers: 0")
        # clear worker indicators
        for w in self.worker_indicators:
            w[0].destroy()
        self.worker_indicators = []
        # clear queued visuals
        self.canvas.delete("all")
        self.queued_visuals.clear()
        self.visual_order.clear()
        self.status_queued.config(text="Queued: 0")

    # ----------------------
    # Visual helpers
    # ----------------------
    def _append_queue_visual(self, task_id):
        """Place a small rectangle with task id into the canvas, horizontally."""
        xbase = 10 + len(self.visual_order) * 70
        if len(self.visual_order) >= self.max_visual_slots:
            # shift left if overflow: remove oldest visual (but keep it logically queued)
            oldest = self.visual_order.pop(0)
            rect_id, txt_id = self.queued_visuals.pop(oldest)
            self.canvas.delete(rect_id)
            self.canvas.delete(txt_id)
            # shift existing visuals left by 70 px
            for tid in list(self.visual_order):
                rect_id, txt_id = self.queued_visuals[tid]
                self.canvas.move(rect_id, -70, 0)
                self.canvas.move(txt_id, -70, 0)
            xbase = 10 + (len(self.visual_order)) * 70

        rect = self.canvas.create_rectangle(xbase, 20, xbase + 60, 80, fill="#ffd966", outline="#c79b3a")
        txt = self.canvas.create_text(xbase + 30, 48, text=str(task_id), font=("Helvetica", 12, "bold"))
        self.queued_visuals[task_id] = (rect, txt)
        self.visual_order.append(task_id)

    def _remove_queue_visual(self, task_id):
        """Remove visual rectangle when the task starts executing."""
        if task_id in self.queued_visuals:
            rect_id, txt_id = self.queued_visuals.pop(task_id)
            try:
                self.canvas.delete(rect_id)
                self.canvas.delete(txt_id)
            except Exception:
                pass
            # also remove from visual_order
            if task_id in self.visual_order:
                self.visual_order.remove(task_id)
                # shift left remaining visuals
                for i, tid in enumerate(self.visual_order):
                    rect_id, txt_id = self.queued_visuals[tid]
                    target_x = 10 + i * 70
                    # find current bbox and move to target (simple approach)
                    self.canvas.coords(rect_id, target_x, 20, target_x + 60, 80)
                    self.canvas.coords(txt_id, target_x + 30, 48)

    def _setup_worker_indicators(self, k):
        """Create small canvas widgets to indicate worker busy/idle status."""
        # destroy previous
        for w in self.worker_indicators:
            w[0].destroy()
        self.worker_indicators.clear()
        for i in range(k):
            c = tk.Canvas(self.worker_frame, width=60, height=24, bg="#ffffff", highlightthickness=0)
            c.pack(side="left", padx=6)
            rect = c.create_rectangle(2, 2, 58, 22, fill="#bdc3c7", outline="#7f8c8d")
            text = c.create_text(30, 12, text=f"W{i}", fill="black", font=("Helvetica", 9, "bold"))
            self.worker_indicators.append((c, rect, text))

    def _set_worker_busy(self, worker_index, busy=True):
        if worker_index < len(self.worker_indicators):
            c, rect, text = self.worker_indicators[worker_index]
            color = "#e74c3c" if busy else "#2ecc71"
            try:
                c.itemconfig(rect, fill=color)
            except Exception:
                pass

    # ----------------------
    # GUI log / queue processing
    # ----------------------
    def log_message(self, s):
        """Append a line to the scrollable log (run in main thread)."""
        self.log.config(state="normal")
        self.log.insert("end", s + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

    def process_gui_queue(self):
        """Process messages from workers and other threads."""
        try:
            while True:
                msg = self.gui_queue.get_nowait()
                if not isinstance(msg, tuple) or len(msg) < 2:
                    continue
                kind = msg[0]
                if kind == "log":
                    _, tstr, text = msg
                    self.log_message(f"{tstr} - {text}")
                elif kind == "task_started":
                    _, task_id = msg
                    # remove the visual box from queue (it moved to worker)
                    self._remove_queue_visual(task_id)
                    self.status_queued.config(text=f"Queued: {len(self.visual_order)}")
                elif kind == "task_finished":
                    _, task_id = msg
                    # nothing else here; logs already added
                    pass
                elif kind == "worker_busy":
                    _, idx, busy = msg
                    self._set_worker_busy(idx, busy)
                # mark processed
                self.gui_queue.task_done()
        except Empty:
            pass
        # schedule next poll
        self.root.after(120, self.process_gui_queue)

    def on_close(self):
        """Handle window close; ensure pool shutdown."""
        if self.pool.workers:
            if messagebox.askyesno("Confirm Exit", "Pool is running. Shutdown and exit?"):
                self.pool.shutdown()
            else:
                return
        self.root.destroy()


# ------------------------------
# Run application
# ------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = ThreadPoolGUI(root)
    root.mainloop()