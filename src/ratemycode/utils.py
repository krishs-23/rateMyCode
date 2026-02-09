
import os
import sqlite3
import datetime
import pyttsx3
import multiprocessing
import threading
import queue
import time
from rich.console import Console

console = Console()

class DatabaseManager:
    """
    Manages SQLite connections via a dedicated writer thread (Producer-Consumer).
    """
    _instance = None
    
    def __new__(cls, db_path=None):
        if cls._instance is None:
            if db_path is None:
                 raise ValueError("DatabaseManager must be initialized with a path first")
            
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance.db_path = db_path
            cls._instance.queue = queue.Queue()
            cls._instance.running = True
            
            # Start the writer thread
            cls._instance.writer_thread = threading.Thread(target=cls._instance._writer_loop, daemon=True)
            cls._instance.writer_thread.start()
            
        return cls._instance

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
             raise RuntimeError("DatabaseManager not initialized")
        return cls._instance

    @classmethod
    def initialize(cls, db_path):
        return cls(db_path)

    def _writer_loop(self):
        """
        Dedicated thread loop that consumes writes from the queue.
        """
        conn = None
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._init_db(conn)
            
            while self.running:
                try:
                    # Blocking get
                    task = self.queue.get()
                    if task is None: # Sentinel processing
                        break
                        
                    filename, score, mode, method = task
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO history (timestamp, filename, score, mode, method) VALUES (?, ?, ?, ?, ?)",
                                (datetime.datetime.now().isoformat(), filename, score, mode, method))
                    conn.commit()
                    self.queue.task_done()
                    
                except queue.Empty:
                    continue
                except Exception as e:
                    console.print(f"[red]DB Write Error during loop: {e}[/red]")
                    
        except Exception as e:
            console.print(f"[red]DB Connection Error: {e}[/red]")
        finally:
            if conn:
                conn.close()

    def _init_db(self, conn):
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                filename TEXT,
                score INTEGER,
                mode TEXT,
                method TEXT
            )
        ''')
        conn.commit()

    def queue_write(self, filename, score, mode, method):
        """
        Safe method to queue a DB write from any thread.
        """
        self.queue.put((filename, score, mode, method))

    def shutdown(self):
        self.running = False
        self.queue.put(None)
        if hasattr(self, 'writer_thread'):
            self.writer_thread.join(timeout=1.0)

def get_feedback(score: int, mode: str) -> tuple[str, str]:
    """
    Generates the feedback string and color based on the score and selected persona mode.
    """
    verdict = ""
    color = "green"
    
    if score >= 90:
        if mode == "SAVAGE":
            verdict = "Shockingly adequate. I'm disappointed I can't roast this."
        elif mode == "PROFESSIONAL":
            verdict = "Excellent work. Adheres to high standards."
        else: # GENTLE
            verdict = "Wonderful! Your code is a shining example."
        color = "green"
    elif score >= 70:
        if mode == "SAVAGE":
            verdict = "It runs, but it smells like mediocrity."
        elif mode == "PROFESSIONAL":
            verdict = "Acceptable, but room for optimization."
        else: # GENTLE
            verdict = "Good job! A few tweaks and it will be perfect."
        color = "yellow"
    else:
        if mode == "SAVAGE":
            verdict = "My CPU hurts just looking at this nested garbage."
        elif mode == "PROFESSIONAL":
            verdict = "Code complexity exceeds recommended limits. Refactor immediately."
        else: # GENTLE
            verdict = "Don't worry, we all write nested loops sometimes. Let's try to flatten it."
        color = "red"
        
    return verdict, color

def persist_result(db_path: str, filename: str, score: int, mode: str, method: str):
    """
    Saves the analysis result into a persistent SQLite database.
    Now delegates to the DatabaseManager singleton queue.
    """
    try:
        # Singleton should already be initialized by main.py
        # But for robustness (or if called from test), lazy init if not present
        try:
             db = DatabaseManager.get_instance()
        except RuntimeError:
             db = DatabaseManager.initialize(db_path)
             
        db.queue_write(filename, score, mode, method)
    except Exception as e:
         console.print(f"[red]Failed to queue DB write: {e}[/red]")

def _speak_process(text: str):
    """
    Target function for valid multiprocessing.
    """
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 170)
        engine.say(text)
        engine.runAndWait()
    except Exception:
        pass

def speak_feedback_async(text: str, voice_enabled: bool):
    """
    Uses Text-to-Speech (TTS) to read the feedback aloud in a separate PROCESS.
    This avoids segfaults on macOS/Linux caused by threading UI libraries.
    """
    if not voice_enabled:
        return

    # Fire and forget process
    p = multiprocessing.Process(target=_speak_process, args=(text,))
    p.start()
