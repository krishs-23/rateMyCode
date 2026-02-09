
import os
import sqlite3
import datetime
import pyttsx3
import multiprocessing
import json
import re
from rich.console import Console

console = Console()

class DatabaseManager:
    """
    Manages SQLite connections to avoid opening/closing on every write.
    """
    _instance = None
    
    def __new__(cls, db_path):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance.db_path = db_path
            cls._instance.conn = None
        return cls._instance

    def connect(self):
        if self.conn is None:
            try:
                os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
                self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
                self._init_db()
            except Exception as e:
                console.print(f"[red]DB Connection Error: {e}[/red]")

    def _init_db(self):
        cursor = self.conn.cursor()
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
        self.conn.commit()

    def insert(self, filename, score, mode, method):
        try:
            self.connect()
            cursor = self.conn.cursor()
            cursor.execute("INSERT INTO history (timestamp, filename, score, mode, method) VALUES (?, ?, ?, ?, ?)",
                        (datetime.datetime.now().isoformat(), filename, score, mode, method))
            self.conn.commit()
        except Exception as e:
            console.print(f"[red]DB Write Error: {e}[/red]")

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

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
    """
    db = DatabaseManager(db_path)
    db.insert(filename, score, mode, method)

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
