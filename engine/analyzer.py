"""
RateMyCode - complexity analyzer and feedback engine.

This script is the core logic engine for the RateMyCode tool. It performs the following tasks:
1. Parses the source code using AST (Abstract Syntax Tree).
2. Calculates the complexity score based on nested loop depth.
3. Generates feedback (text and audio) based on the configured 'Persona'.
4. Persists the results to a local SQLite database for historical tracking.
"""

import sys
import ast
import sqlite3
import datetime
import os
from typing import Tuple

# Attempt to import third-party libraries.
# If these fail, the script cannot run properly, so we exit with a clear error.
try:
    import pyttsx3
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
except ImportError:
    print("Error: Required libraries not found. Please install requirements.txt")
    sys.exit(1)

# Initialize Rich Console for styled terminal output
console = Console()

class ComplexityVisitor(ast.NodeVisitor):
    """
    AST Visitor to traverse the code structure and determine maximum nesting depth.
    Specifically looks for 'For' loops and 'While' loops.
    """
    def __init__(self):
        self.max_depth = 0      # Tracks the deepest nesting found in the entire file
        self.current_depth = 0  # Tracks depth of the current traversal node

    def visit_For(self, node):
        """
        Called when a 'for' loop is encountered.
        Increments depth, checks if it's a new record, visits children, then decrements.
        """
        self.current_depth += 1
        self.max_depth = max(self.max_depth, self.current_depth)
        self.generic_visit(node) # Continue traversing inside the loop
        self.current_depth -= 1

    def visit_While(self, node):
        """
        Called when a 'while' loop is encountered.
        Same logic as visit_For.
        """
        self.current_depth += 1
        self.max_depth = max(self.max_depth, self.current_depth)
        self.generic_visit(node)
        self.current_depth -= 1
    
    def visit_FunctionDef(self, node):
        """
        Called when a function definition is encountered.
        We continue traversal without resetting depth because complexity accumulates.
        """
        self.generic_visit(node)

def analyze_complexity(code: str) -> int:
    """
    Parses the code string into an AST and calculates the max nesting depth.
    
    Args:
        code (str): The raw source code content.
        
    Returns:
        int: The maximum depth of nested loops found (e.g., 3 for O(n^3)).
             Returns -1 if a SyntaxError occurs.
    """
    try:
        tree = ast.parse(code)
        visitor = ComplexityVisitor()
        visitor.visit(tree)
        return visitor.max_depth
    except SyntaxError:
        return -1
    except Exception as e:
        console.print(f"[red]Error analyzing code: {e}[/red]")
        return -1

def get_feedback(score: int, mode: str) -> Tuple[str, str]:
    """
    Generates the feedback string and color based on the score and selected persona mode.
    
    Args:
        score (int): The calculated quality score (0-100).
        mode (str): The persona mode ('SAVAGE', 'PROFESSIONAL', 'GENTLE').
        
    Returns:
        Tuple[str, str]: (Verdict Text, Color String for Rich)
    """
    # Modes: SAVAGE, PROFESSIONAL, GENTLE
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

def persist_result(filename: str, score: int, mode: str):
    """
    Saves the analysis result into a persistent SQLite database.
    Creates the table 'history' if it doesn't already exist.
    """
    try:
        # Locate DB in the parent directory (project root)
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rateMyCode_history.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Ensure schema exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                filename TEXT,
                score INTEGER,
                mode TEXT
            )
        ''')
        
        # Insert record
        cursor.execute("INSERT INTO history (timestamp, filename, score, mode) VALUES (?, ?, ?, ?)",
                       (datetime.datetime.now().isoformat(), filename, score, mode))
        conn.commit()
    except Exception as e:
        console.print(f"[red]Database Error: {e}[/red]")
    finally:
        if 'conn' in locals():
            conn.close()

def speak_feedback(text: str, voice_enabled: str):
    """
    Uses Text-to-Speech (TTS) to read the feedback aloud.
    Only proceeds if voice_enabled is "true".
    """
    if voice_enabled.lower() != "true":
        return
    
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 170) # Set speed
        engine.say(text)
        engine.runAndWait()             # Block until speech is finished
    except Exception:
        # Fail silently if audio drivers are missing/broken on the host system
        pass

def main():
    """
    Main Execution Flow:
    1. Validate Arguments
    2. Read File
    3. Analyze Complexity (with visual loading bar)
    4. Calculate Score
    5. Save to DB
    6. Display Results (Table)
    7. Speak Results (Audio)
    """
    
    # 1. Argument Validation
    if len(sys.argv) < 4:
        console.print("[red]Usage: python analyzer.py <filepath> <mode> <voice_enabled>[/red]")
        sys.exit(1)

    filepath = sys.argv[1]
    mode = sys.argv[2]
    voice_enabled = sys.argv[3]

    if not os.path.exists(filepath):
        console.print(f"[red]File not found: {filepath}[/red]")
        sys.exit(1)

    # 2. Read File Content
    with open(filepath, 'r') as f:
        code = f.read()

    # 3. Analyze Complexity (with visuals)
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        progress.add_task(description="Analyzing Code...", total=None)
        
        # Simulate processing time for UX effect
        import time
        time.sleep(0.5) 
        
        depth = analyze_complexity(code)

    # Handle Syntax Errors
    if depth == -1:
        console.print(f"[bold red]Syntax Error in {os.path.basename(filepath)}[/bold red]")
        verdict = "Your code is so broken I can't even analyze it."
        speak_feedback(verdict, voice_enabled)
        return

    # 4. Scoring Algorithm
    # Formula: Start at 100. Deduct 20 points for every level of nesting depth.
    # Depth 0 (No loops) = 100
    # Depth 1 (O(n)) = 80
    # Depth 2 (O(n^2)) = 60
    # Depth 3 (O(n^3)) = 40 (This is usually considered bad practice)
    score = max(0, 100 - (depth * 20))

    # 5. Persist Data
    persist_result(os.path.basename(filepath), score, mode)
    
    # Generate Feedback Text
    verdict_text, color = get_feedback(score, mode)

    # 6. Display Results using Rich Table
    table = Table(title=f"RateMyCode: {os.path.basename(filepath)}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")
    table.add_column("Verdict", style=color)

    table.add_row("Complexity (Depth)", str(depth), "High" if depth > 2 else "Acceptable")
    table.add_row("Quality Score", f"{score}/100", verdict_text)

    console.print(table)
    
    # 7. Audio Feedback (Threshold: < 80 score triggers speech)
    if score < 80:
        speak_feedback(verdict_text, voice_enabled)

if __name__ == "__main__":
    main()
