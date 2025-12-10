"""
v9_timeline.py
Version 9: Simple Thread Timeline Visualization

Run:
    python v9_timeline.py
"""
import threading
from queue import Queue, Empty
import time
import tkinter as tk
from tkinter import scrolledtext, messagebox
from datetime import datetime
import random

# -----------------------------
# ThreadPool (workers only send GUI messages)
# -----------------------------
class ThreadPool:
    def __init__(self):
        self.tasks = Queue()
        self.workers = []           # list of (Thread, index)
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
            self.workers.append((t, i))

    def add_worker(self, gui_queue=None):
        idx = len(self.workers)
        t = threading.Thread(target=self._worker_loop, args=(idx, gui_queue), daemon=True)
        t.start()
        self.workers.append((t, idx))
        return idx

    def remove_worker(self):
        if not self.workers:
            return False
        # signal: put None so one worker exits
        self.tasks.put(None)
        return True

    def submit(self, task_callable):
        with self.lock:
            tid = self.next_task_id
            self.next_task_id += 1
        self.tasks.put((tid, task_callable))
        return tid

    def _worker_loop(self, worker_index, gui_queue):
        while not self.stop_event.is_set():
            try:
                item = self.tasks.get(timeout=0.2)
            except Empty:
                continue
            if item is None:
                self.tasks.task_done()
                break
            task_id, task_callable = item
            # signal GUI that task started (include estimated duration if available)
            if gui_queue:
                # Worker doesn't know duration, but we send a "start" before execution.
                gui_queue.put(("task_started", task_id, worker_index, timestamp()))
            try:
                task_callable()
            except Exception as e:
                if gui_queue:
                    gui_queue.put(("log", timestamp(), f"Task {task_id} error: {e}"))
            # signal GUI that task finished
            if gui_queue:
                gui_queue.put(("task_finished", task_id, worker_index, timestamp()))
            self.tasks.task_done()

    def shutdown(self):
        self.stop_event.set()
        # send sentinel for each worker to exit quickly
        for _ in self.workers:
            self.tasks.put(None)
        for t, _ in self.workers:
            t.join()
        self.workers.clear()

# -----------------------------
# Helpers
# -----------------------------
def timestamp():
    return datetime.now().strftime("%H:%M:%S")

def make_sleep_task(duration_ms):
    """Return a callable that sleeps for duration_ms milliseconds."""
    def task():
        time.sleep(duration_ms / 1000.0)
    return task

def color_for_index(i):
    palette = ["#3498db","#2ecc71","#f1c40f","#9b59b6","#e67e22","#1abc9c","#e74c3c"]
    return palette[i % len(palette)]

# -----------------------------
# GUI: includes timeline visualization
# -----------------------------
class TimelineGUI:
    def __init__(self, root):
        self.root = root
        root.title("Thread Timeline Visualizer - v9")
        root.geometry("980x620")
        self.gui_queue = Queue()
        self.pool = ThreadPool()

        # visual bookkeeping
        self.timeline_lane_height = 28
        self.timeline_margin = 6
        self.lanes = []               # one lane per worker: dicts with start_x (next x), canvas ids
        self.active_bars = {}         # task_id -> bar info {'rect', 'lane', 'start_x', 'target_width'}
        self.bar_speed_px_per_tick = 5   # growth speed (visual); not tied to real time exactly
        self.anim_tick_ms = 80

        # queued visuals (small boxes)
        self.queued_visuals = {}
        self.visual_order = []

        # Build UI
        self._build_ui()

        # Poll GUI queue
        self.root.after(120, self._process_gui_queue)
        self.root.after(self.anim_tick_ms, self._step_bars)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        # Left controls
        left = tk.Frame(self.root, width=300, bg="#f6f7f9")
        left.pack(side="left", fill="y", padx=8, pady=8)

        tk.Label(left, text="Thread Timeline Controller", font=("Arial", 14, "bold"), bg="#f6f7f9").pack(pady=(6,12))

        tk.Label(left, text="Initial workers:", bg="#f6f7f9").pack(anchor="w", padx=8)
        self.init_workers_entry = tk.Entry(left, width=8)
        self.init_workers_entry.insert(0, "4")
        self.init_workers_entry.pack(padx=8, pady=(0,8))

        self.create_btn = tk.Button(left, text="Create Pool", bg="#28a745", fg="white", width=18, command=self._create_pool)
        self.create_btn.pack(padx=8, pady=4)

        dynf = tk.Frame(left, bg="#f6f7f9")
        dynf.pack(pady=6)
        tk.Button(dynf, text="Add Worker", width=10, command=self._add_worker).pack(side="left", padx=6)
        tk.Button(dynf, text="Remove Worker", width=12, command=self._remove_worker).pack(side="left", padx=6)

        tk.Label(left, text="Task duration (ms):", bg="#f6f7f9").pack(anchor="w", padx=8, pady=(8,0))
        self.dur_scale = tk.Scale(left, from_=100, to=3000, orient="horizontal", length=220, bg="#f6f7f9")
        self.dur_scale.set(700)
        self.dur_scale.pack(padx=8, pady=(0,8))

        tk.Button(left, text="Add Task", bg="#007bff", fg="white", width=18, command=self._add_task).pack(padx=8, pady=6)

        self.lbl_pool = tk.Label(left, text="Pool: Not created", bg="#f6f7f9")
        self.lbl_pool.pack(padx=8, pady=(12,2))
        self.lbl_workers = tk.Label(left, text="Workers: 0", bg="#f6f7f9")
        self.lbl_workers.pack(padx=8, pady=2)
        self.lbl_queued = tk.Label(left, text="Queued: 0", bg="#f6f7f9")
        self.lbl_queued.pack(padx=8, pady=2)

        # Right: timeline canvas + log
        right = tk.Frame(self.root, bg="#ffffff")
        right.pack(side="right", expand=True, fill="both", padx=8, pady=8)

        tk.Label(right, text="Timeline (per-thread lanes):", bg="#ffffff", font=("Arial", 12)).pack(anchor="nw")
        self.timeline_canvas = tk.Canvas(right, height=250, bg="#ffffff", highlightthickness=1, highlightbackground="#ddd")
        self.timeline_canvas.pack(fill="x", padx=6, pady=(6,8))

        tk.Label(right, text="Queued Tasks (visual):", bg="#ffffff", font=("Arial", 12)).pack(anchor="nw")
        self.queue_canvas = tk.Canvas(right, height=80, bg="#fbfbfb", highlightthickness=1, highlightbackground="#eee")
        self.queue_canvas.pack(fill="x", padx=6, pady=(6,8))

        tk.Label(right, text="Live Log:", bg="#ffffff", font=("Arial", 12)).pack(anchor="nw")
        self.log = scrolledtext.ScrolledText(right, state="disabled", height=12)
        self.log.pack(fill="both", expand=True, padx=6, pady=(6,0))

    # ---------------------
    # Pool / UI handlers
    # ---------------------
    def _create_pool(self):
        if self.pool.workers:
            messagebox.showinfo("Info", "Pool already created")
            return
        try:
            k = int(self.init_workers_entry.get())
            assert k > 0
        except Exception:
            messagebox.showerror("Error", "Enter positive integer for workers")
            return
        self.pool.create(k, gui_queue=self.gui_queue)
        self._setup_lanes(k)
        self.create_btn.config(state="disabled")
        self.lbl_pool.config(text="Pool: Running")
        self.lbl_workers.config(text=f"Workers: {k}")
        self._log(f"{timestamp()} - Pool created ({k} workers)")

    def _add_worker(self):
        if not self.pool.workers:
            messagebox.showwarning("Warning", "Create pool first")
            return
        idx = self.pool.add_worker(gui_queue=self.gui_queue)
        self._setup_lanes(len(self.pool.workers))
        self.lbl_workers.config(text=f"Workers: {len(self.pool.workers)}")
        self._log(f"{timestamp()} - Worker {idx} added")

    def _remove_worker(self):
        if not self.pool.workers:
            messagebox.showwarning("Warning", "No workers to remove")
            return
        if self.pool.remove_worker():
            self._log(f"{timestamp()} - Removal signal sent to a worker")

    def _add_task(self):
        if not self.pool.workers:
            messagebox.showwarning("Warning", "Create pool first")
            return
        dur = self.dur_scale.get()
        tid = self.pool.submit(make_sleep_task(dur))
        self._append_queue_box(tid)
        self.lbl_queued.config(text=f"Queued: {len(self.visual_order)}")
        self._log(f"{timestamp()} - Task {tid} queued (duration {dur} ms)")

    def _shutdown(self):
        if self.pool.workers:
            self.pool.shutdown()
        self._log(f"{timestamp()} - Pool shutdown (manual)")

    # ---------------------
    # Timeline lanes & bars
    # ---------------------
    def _setup_lanes(self, count):
        # clear canvas and recompute lanes
        self.timeline_canvas.delete("all")
        self.lanes.clear()
        height = self.timeline_canvas.winfo_height() or 250
        lane_h = self.timeline_lane_height
        for i in range(count):
            y0 = self.timeline_margin + i * (lane_h + self.timeline_margin)
            y1 = y0 + lane_h
            # background rect for lane
            lane_bg = self.timeline_canvas.create_rectangle(0, y0, 1000, y1, fill="#f8f9fb", outline="")
            # lane label
            self.timeline_canvas.create_text(6, (y0+y1)/2, anchor="w", text=f"W{i}", font=("Arial", 9, "bold"))
            # next x start for new bars
            lane_info = {'index': i, 'next_x': 40, 'y0': y0, 'y1': y1}
            self.lanes.append(lane_info)

    def _start_bar_for_task(self, task_id, worker_index, duration_ms):
        """Create a new bar on the worker lane for the task and track it."""
        if worker_index >= len(self.lanes):
            return
        lane = self.lanes[worker_index]
        sx = lane['next_x']
        sy0 = lane['y0'] + 4
        sy1 = lane['y1'] - 4
        # initial tiny bar
        rect = self.timeline_canvas.create_rectangle(sx, sy0, sx+4, sy1, fill=color_for_index(worker_index), outline="")
        # store expected pixel target based on duration (simple scale: pixels per ms)
        pixels_per_ms = 0.06  # tweak for visible growth; simple mapping
        target_width = max(8, int(duration_ms * pixels_per_ms))
        self.active_bars[task_id] = {'rect': rect, 'lane': worker_index, 'current_w': 4, 'target_w': target_width, 'sx': sx}
        # reserve space for next bar (leave small gap)
        lane['next_x'] += target_width + 8

    def _grow_bars_tick(self):
        # increase each active bar by bar_speed_px_per_tick until target reached
        to_remove = []
        for tid, b in list(self.active_bars.items()):
            grow = self.bar_speed_px_per_tick
            if b['current_w'] >= b['target_w']:
                continue
            new_w = min(b['target_w'], b['current_w'] + grow)
            x1 = b['sx'] + new_w
            # update rectangle coords
            self.timeline_canvas.coords(b['rect'], b['sx'], self.lanes[b['lane']]['y0'] + 4, x1, self.lanes[b['lane']]['y1'] - 4)
            b['current_w'] = new_w
        # done (no removal here; finish when task_finished arrives)

    def _step_bars(self):
        # animate growth
        self._grow_bars_tick()
        self.root.after(self.anim_tick_ms, self._step_bars)

    # ---------------------
    # Queue visual (small boxes)
    # ---------------------
    def _append_queue_box(self, task_id):
        x = 8 + len(self.visual_order) * 54
        if len(self.visual_order) >= 10:
            # simple behavior: pop oldest visual
            old = self.visual_order.pop(0)
            if old in self.queued_visuals:
                r, t = self.queued_visuals.pop(old)
                try:
                    self.queue_canvas.delete(r); self.queue_canvas.delete(t)
                except Exception:
                    pass
            # shift left remaining
            for i, tid in enumerate(self.visual_order):
                r, t = self.queued_visuals[tid]
                tx = 8 + i * 54
                self.queue_canvas.coords(r, tx, 10, tx + 46, 70)
                self.queue_canvas.coords(t, tx + 23, 40)
            x = 8 + len(self.visual_order) * 54
        rect = self.queue_canvas.create_rectangle(x, 10, x + 46, 70, fill="#ffd966", outline="#c79b3a")
        txt = self.queue_canvas.create_text(x + 23, 40, text=str(task_id))
        self.queued_visuals[task_id] = (rect, txt)
        self.visual_order.append(task_id)

    def _remove_queue_box(self, task_id):
        if task_id in self.queued_visuals:
            r, t = self.queued_visuals.pop(task_id)
            try:
                self.queue_canvas.delete(r); self.queue_canvas.delete(t)
            except Exception:
                pass
            if task_id in self.visual_order:
                self.visual_order.remove(task_id)
                for i, tid in enumerate(self.visual_order):
                    r2, t2 = self.queued_visuals[tid]
                    nx = 8 + i * 54
                    self.queue_canvas.coords(r2, nx, 10, nx + 46, 70)
                    self.queue_canvas.coords(t2, nx + 23, 40)
    # GUI queue processing (messages from workers)
 
    def _process_gui_queue(self):
        try:
            while True:
                msg = self.gui_queue.get_nowait()
                if not isinstance(msg, tuple) or not msg:
                    continue
                kind = msg[0]
                if kind == "log":
                    _, tstr, text = msg
                    self._log(f"{tstr} - {text}")
                elif kind == "task_started":
                    _, task_id, widx, tstart = msg
                    # when worker picks the task, remove from queued visuals and create timeline bar
                    self._remove_queue_box(task_id)
                    self.lbl_queued.config(text=f"Queued: {len(self.visual_order)}")
                    
                    duration_ms = task_duration_map.pop(task_id, 700)
                    self._start_bar_for_task(task_id, widx, duration_ms)
                    self._log(f"{timestamp()} - Task {task_id} started on W{widx} (dur {duration_ms}ms)")
                elif kind == "task_finished":
                    _, task_id, widx, tend = msg
                    # when finished, we can mark bar as complete (set full width immediately)
                    if task_id in self.active_bars:
                        b = self.active_bars[task_id]
                        # set to final width instantly
                        final = b['sx'] + b['target_w']
                        self.timeline_canvas.coords(b['rect'], b['sx'], self.lanes[b['lane']]['y0'] + 4, final, self.lanes[b['lane']]['y1'] - 4)
                        # optionally remove from active_bars to stop further growth
                        del self.active_bars[task_id]
                    self._log(f"{timestamp()} - Task {task_id} finished on W{widx}")
                self.gui_queue.task_done()
        except Empty:
            pass
        self.root.after(120, self._process_gui_queue)

    # Logging helper
    def _log(self, s):
        self.log.config(state="normal")
        self.log.insert("end", s + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

    def _on_close(self):
        if self.pool.workers:
            if messagebox.askyesno("Confirm", "Pool is running. Shutdown and exit?"):
                self.pool.shutdown()
            else:
                return
        self.root.destroy()

task_duration_map = {}


if __name__ == "__main__":
    root = tk.Tk()
    gui = TimelineGUI(root)
    
    original_submit = gui.pool.submit

    def wrapped_submit_with_duration(task_callable, duration_ms=None):
        # use original to get tid, but original expects only callable. We'll call it and then store duration.
        tid = original_submit(task_callable)
        if duration_ms is None:
            duration_ms = 700
        task_duration_map[tid] = duration_ms
        return tid

    gui.pool.submit = wrapped_submit_with_duration

    # start main loop
    root.mainloop()