
import os
import sqlite3
import datetime
import pyttsx3
import threading
from rich.console import Console

console = Console()

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
    try:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        conn = sqlite3.connect(db_path)
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
        
        cursor.execute("INSERT INTO history (timestamp, filename, score, mode, method) VALUES (?, ?, ?, ?, ?)",
                       (datetime.datetime.now().isoformat(), filename, score, mode, method))
        conn.commit()
    except Exception as e:
        console.print(f"[red]Database Error: {e}[/red]")
    finally:
        if 'conn' in locals():
            conn.close()

def speak_feedback_async(text: str, voice_enabled: bool):
    """
    Uses Text-to-Speech (TTS) to read the feedback aloud in a separate thread.
    """
    if not voice_enabled:
        return

    def _speak():
        try:
            engine = pyttsx3.init()
            engine.setProperty('rate', 170)
            engine.say(text)
            engine.runAndWait()
        except Exception:
            pass

    threading.Thread(target=_speak, daemon=True).start()
