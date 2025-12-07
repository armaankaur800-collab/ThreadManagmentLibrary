"""
v5_threadpool_gui.py
Version 5: Adds simple task movement animation to the v4 ThreadPool GUI.

Run:
    python v5_threadpool_gui.py

Notes:
- This extends the v4 design: tasks are queued visually; when a worker starts a task,
  a small circle animates from the queue region to the worker indicator.
- GUI updates remain thread-safe via gui_queue.
- Keep this file single-file for easy commits and understanding.
"""

import threading
from queue import Queue, Empty
import time
import tkinter as tk
from tkinter import scrolledtext, messagebox
from datetime import datetime

# ------------------------------
# ThreadPool implementation (same core as v4)
# ------------------------------
class ThreadPool:
    def __init__(self):
        self.tasks = Queue()
        self.workers = []
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.next_task_id = 1

    def create(self, n, gui_queue=None):
        if self.workers:
            return
        self.stop_event.clear()
        for i in range(n):
            t = threading.Thread(target=self._worker_loop, args=(i, gui_queue), daemon=True)
            t.start()
            self.workers.append(t)

    def _worker_loop(self, worker_index, gui_queue):
        while not self.stop_event.is_set():
            try:
                task_info = self.tasks.get(timeout=0.2)
            except Empty:
                continue
            if task_info is None:
                self.tasks.task_done()
                break
            task_id, task_callable = task_info
            if gui_queue:
                gui_queue.put(("log", timestamp(), f"Task {task_id} started on worker {worker_index}"))
                gui_queue.put(("task_started", task_id, worker_index))
            try:
                task_callable()
            except Exception as e:
                if gui_queue:
                    gui_queue.put(("log", timestamp(), f"Task {task_id} raised exception: {e}"))
            if gui_queue:
                gui_queue.put(("log", timestamp(), f"Task {task_id} finished on worker {worker_index}"))
                gui_queue.put(("task_finished", task_id, worker_index))
            self.tasks.task_done()

    def submit(self, task_callable):
        with self.lock:
            tid = self.next_task_id
            self.next_task_id += 1
        self.tasks.put((tid, task_callable))
        return tid

    def shutdown(self):
        self.stop_event.set()
        for _ in self.workers:
            self.tasks.put(None)
        for t in self.workers:
            t.join()
        self.workers = []

# ------------------------------
# Helpers
# ------------------------------
def timestamp():
    return datetime.now().strftime("%H:%M:%S")

def make_sample_task(duration_ms=700):
    def task():
        time.sleep(duration_ms / 1000.0)
    return task

# ------------------------------
# GUI Application with animation
# ------------------------------
class ThreadPoolGUIv5:
    def __init__(self, root):
        self.root = root
        root.title("ThreadPool Visualizer - Version 5 (Animation)")
        root.geometry("980x620")
        self.gui_queue = Queue()

        # ThreadPool
        self.pool = ThreadPool()

        # Visual state
        self.queued_visuals = {}     # task_id -> (rect_id, text_id)  (rect here used for label background)
        self.visual_order = []       # ordered list of task_ids
        self.task_count = 0
        self.max_visual_slots = 12

        # Animation state
        self.animations = []         # list of dicts: { 'id': canvas_id, 'x','y','tx','ty','steps','step' }
        self.anim_tick_ms = 40       # animation update every 40ms (~25fps)

        # Layout
        self._build_layout()

        # Start polling queues
        self.root.after(120, self.process_gui_queue)
        self.root.after(self.anim_tick_ms, self.step_animations)

        # close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_layout(self):
        # Left control panel
        self.left = tk.Frame(self.root, width=320, bg="#f5f5f5")
        self.left.pack(side="left", fill="y", padx=8, pady=8)

        tk.Label(self.left, text="ThreadPool Controller", font=("Helvetica", 14, "bold"), bg="#f5f5f5").pack(pady=(6,12))
        tk.Label(self.left, text="Threads:", bg="#f5f5f5").pack(anchor="w", padx=12)
        self.thread_entry = tk.Entry(self.left, width=10)
        self.thread_entry.insert(0, "4")
        self.thread_entry.pack(padx=12, pady=6)

        self.create_btn = tk.Button(self.left, text="Create Pool", bg="#27ae60", fg="white", width=20, command=self.create_pool)
        self.create_btn.pack(padx=12, pady=6)
        self.add_btn = tk.Button(self.left, text="Add Task", bg="#2980b9", fg="white", width=20, command=self.add_task, state="disabled")
        self.add_btn.pack(padx=12, pady=6)
        self.shutdown_btn = tk.Button(self.left, text="Shutdown", bg="#c0392b", fg="white", width=20, command=self.shutdown_pool, state="disabled")
        self.shutdown_btn.pack(padx=12, pady=6)

        tk.Label(self.left, text="Task duration (ms):", bg="#f5f5f5").pack(anchor="w", padx=12, pady=(12,0))
        self.duration_scale = tk.Scale(self.left, from_=100, to=3000, orient="horizontal", length=240, bg="#f5f5f5")
        self.duration_scale.set(700)
        self.duration_scale.pack(padx=12, pady=(0,12))

        self.status_pool = tk.Label(self.left, text="Pool Status: Not created", bg="#f5f5f5")
        self.status_pool.pack(padx=12, pady=(8,4))
        self.status_workers = tk.Label(self.left, text="Workers: 0", bg="#f5f5f5")
        self.status_workers.pack(padx=12, pady=2)
        self.status_queued = tk.Label(self.left, text="Queued: 0", bg="#f5f5f5")
        self.status_queued.pack(padx=12, pady=2)

        # Right panel
        self.right = tk.Frame(self.root, bg="#ffffff")
        self.right.pack(side="right", expand=True, fill="both", padx=8, pady=8)

        tk.Label(self.right, text="Task Queue (visual):", font=("Helvetica",12), bg="#ffffff").pack(anchor="nw", padx=10, pady=(6,0))
        self.canvas = tk.Canvas(self.right, height=120, bg="#ffffff", highlightthickness=1, highlightbackground="#ddd")
        self.canvas.pack(fill="x", padx=10, pady=(4,8))

        tk.Label(self.right, text="Workers:", font=("Helvetica",12), bg="#ffffff").pack(anchor="nw", padx=10)
        self.worker_frame = tk.Frame(self.right, bg="#ffffff")
        self.worker_frame.pack(anchor="nw", padx=10, pady=(4,8))
        self.worker_indicators = []

        tk.Label(self.right, text="Live Log (timestamped):", font=("Helvetica",12), bg="#ffffff").pack(anchor="nw", padx=10)
        self.log = scrolledtext.ScrolledText(self.right, state="disabled", height=18)
        self.log.pack(fill="both", expand=True, padx=10, pady=(4,10))

    # -------------------
    # Core wiring
    # -------------------
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

        self._setup_worker_indicators(k)
        self.pool.create(k, gui_queue=self.gui_queue)
        self.create_btn.config(state="disabled")
        self.add_btn.config(state="normal")
        self.shutdown_btn.config(state="normal")
        self.status_pool.config(text="Pool Status: Running")
        self.status_workers.config(text=f"Workers: {k}")
        self.log_message(f"{timestamp()} - Pool created with {k} workers")

    def add_task(self):
        dur = self.duration_scale.get()
        tid = self.pool.submit(make_sample_task(dur))
        self.task_count += 1
        self._append_queue_visual(tid)
        self.status_queued.config(text=f"Queued: {len(self.visual_order)}")
        self.log_message(f"{timestamp()} - Task {tid} queued (duration {dur} ms)")

    def shutdown_pool(self):
        if not self.pool.workers:
            return
        self.pool.shutdown()
        self.log_message(f"{timestamp()} - Pool shutdown initiated")
        self.create_btn.config(state="normal")
        self.add_btn.config(state="disabled")
        self.shutdown_btn.config(state="disabled")
        self.status_pool.config(text="Pool Status: Not created")
        self.status_workers.config(text="Workers: 0")
        for w in self.worker_indicators:
            w[0].destroy()
        self.worker_indicators = []
        # clear canvas visuals and animations
        self.canvas.delete("all")
        self.queued_visuals.clear()
        self.visual_order.clear()
        self.status_queued.config(text="Queued: 0")
        self.animations.clear()

    # -------------------
    # Visual helpers (queue and worker indicators)
    # -------------------
    def _append_queue_visual(self, task_id):
        xbase = 10 + len(self.visual_order) * 72
        if len(self.visual_order) >= self.max_visual_slots:
            oldest = self.visual_order.pop(0)
            rect_id, txt_id = self.queued_visuals.pop(oldest)
            try:
                self.canvas.delete(rect_id)
                self.canvas.delete(txt_id)
            except Exception:
                pass
            for i, tid in enumerate(self.visual_order):
                rect_id, txt_id = self.queued_visuals[tid]
                target_x = 10 + i * 72
                self.canvas.coords(rect_id, target_x, 20, target_x + 62, 100)
                self.canvas.coords(txt_id, target_x + 31, 60)
            xbase = 10 + len(self.visual_order) * 72

        rect = self.canvas.create_rectangle(xbase, 20, xbase + 62, 100, fill="#ffd966", outline="#c79b3a")
        txt = self.canvas.create_text(xbase + 31, 60, text=str(task_id), font=("Helvetica", 12, "bold"))
        self.queued_visuals[task_id] = (rect, txt)
        self.visual_order.append(task_id)

    def _remove_queue_visual(self, task_id):
        if task_id in self.queued_visuals:
            rect_id, txt_id = self.queued_visuals.pop(task_id)
            try:
                self.canvas.delete(rect_id)
                self.canvas.delete(txt_id)
            except Exception:
                pass
            if task_id in self.visual_order:
                self.visual_order.remove(task_id)
                for i, tid in enumerate(self.visual_order):
                    rect_id, txt_id = self.queued_visuals[tid]
                    target_x = 10 + i * 72
                    self.canvas.coords(rect_id, target_x, 20, target_x + 62, 100)
                    self.canvas.coords(txt_id, target_x + 31, 60)

    def _setup_worker_indicators(self, k):
        for w in self.worker_indicators:
            w[0].destroy()
        self.worker_indicators.clear()
        for i in range(k):
            c = tk.Canvas(self.worker_frame, width=70, height=28, bg="#ffffff", highlightthickness=0)
            c.pack(side="left", padx=6)
            rect = c.create_rectangle(2, 2, 68, 26, fill="#95a5a6", outline="#7f8c8d")
            text = c.create_text(35, 14, text=f"W{i}", fill="black", font=("Helvetica", 9, "bold"))
            self.worker_indicators.append((c, rect, text))

    def _set_worker_busy(self, worker_index, busy=True):
        if worker_index < len(self.worker_indicators):
            c, rect, text = self.worker_indicators[worker_index]
            color = "#e74c3c" if busy else "#2ecc71"
            try:
                c.itemconfig(rect, fill=color)
            except Exception:
                pass

    # -------------------
    # Animation logic
    # -------------------
    def launch_animation_to_worker(self, task_id, worker_index):
        """Create a simple circle at the approximate queue location and animate to worker indicator center."""
        # find initial position (if the task rectangle still exists, use its coords; else spawn at left)
        if task_id in self.queued_visuals:
            rect_id, txt_id = self.queued_visuals[task_id]
            coords = self.canvas.coords(rect_id)  # x1,y1,x2,y2
            start_x = (coords[0] + coords[2]) / 2
            start_y = (coords[1] + coords[3]) / 2
        else:
            start_x, start_y = 10, 60

        # target: center of worker indicator in screen coords -> map to canvas coordinates
        # get worker widget position relative to canvas: use winfo_root and canvas.winfo_root to compute offsets
        try:
            w_canvas_root_x = self.canvas.winfo_rootx()
            w_canvas_root_y = self.canvas.winfo_rooty()
            worker_canvas, _, _ = self.worker_indicators[worker_index]
            wx = worker_canvas.winfo_rootx()
            wy = worker_canvas.winfo_rooty()
            # compute target relative to canvas
            tx = (wx - w_canvas_root_x) + 35  # 35 ~ center of worker canvas
            ty = (wy - w_canvas_root_y) + 14
        except Exception:
            # fallback: animate to a default near-right spot
            tx = 700
            ty = 60

        # create circle on canvas
        cid = self.canvas.create_oval(start_x-8, start_y-8, start_x+8, start_y+8, fill="#3498db", outline="#21618c")
        anim = {
            'cid': cid,
            'x': start_x,
            'y': start_y,
            'tx': tx,
            'ty': ty,
            'steps': max(6, int(500 / self.anim_tick_ms)),  # ~500ms movement
            'step': 0,
            'task_id': task_id,
            'worker_index': worker_index
        }
        self.animations.append(anim)

    def step_animations(self):
        # advance each animation one step
        new_anims = []
        for a in self.animations:
            a['step'] += 1
            t = a['step'] / a['steps']
            if t > 1.0: t = 1.0
            nx = a['x'] + (a['tx'] - a['x']) * t
            ny = a['y'] + (a['ty'] - a['y']) * t
            # update canvas oval center
            try:
                self.canvas.coords(a['cid'], nx-8, ny-8, nx+8, ny+8)
            except Exception:
                continue
            if a['step'] >= a['steps']:
                # animation finished: remove circle and pulse worker
                try:
                    self.canvas.delete(a['cid'])
                except Exception:
                    pass
                # pulse worker indicator (brief busy flash) via gui_queue to reuse existing mechanism
                self.gui_queue.put(("worker_busy", a['worker_index'], True))
                # schedule clearing busy after short pause
                self.root.after(350, lambda idx=a['worker_index']: self.gui_queue.put(("worker_busy", idx, False)))
            else:
                new_anims.append(a)
        self.animations = new_anims
        # schedule next tick
        self.root.after(self.anim_tick_ms, self.step_animations)

    # -------------------
    # Process gui_queue: same as v4 but with animation trigger on task_started
    # -------------------
    def process_gui_queue(self):
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
                    # msg: ("task_started", task_id, worker_index)
                    _, task_id, worker_index = msg
                    # remove queued visual
                    self._remove_queue_visual(task_id)
                    self.status_queued.config(text=f"Queued: {len(self.visual_order)}")
                    # launch simple animation from last-known queue spot to worker
                    self.launch_animation_to_worker(task_id, worker_index)
                elif kind == "task_finished":
                    # currently just log exists already
                    pass
                elif kind == "worker_busy":
                    _, idx, busy = msg
                    self._set_worker_busy(idx, busy)
                self.gui_queue.task_done()
        except Empty:
            pass
        self.root.after(120, self.process_gui_queue)

    def log_message(self, s):
        self.log.config(state="normal")
        self.log.insert("end", s + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

    def on_close(self):
        if self.pool.workers:
            if messagebox.askyesno("Confirm Exit", "Pool is running. Shutdown and exit?"):
                self.pool.shutdown()
            else:
                return
        self.root.destroy()

# ------------------------------
# Run
# ------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = ThreadPoolGUIv5(root)
    root.mainloop()