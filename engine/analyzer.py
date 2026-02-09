"""
RateMyCode - complexity analyzer and feedback engine.

This script is the core logic engine for the RateMyCode tool. It performs the following tasks:
1. Parses the source code using AST (Abstract Syntax Tree).
2. Calculates the complexity score based on nested loop depth.
3. Generates feedback (text and audio) based on the configured 'Persona'.
4. Persists the results to a local SQLite database for historical tracking.
5. (Optional) Uses Gemini API for dynamic AI feedback.
"""

import sys
import ast
import sqlite3
import datetime
import os
import re
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

# Import Google GenAI (Soft import to avoid crashing if not used but package missing)
try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

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

def analyze_with_gemini(api_key: str, code: str, mode: str) -> Tuple[int, str]:
    """
    Uses Gemini API to analyze the code.
    Fallback to AST if API fails.
    Returns (Score, Verdict).
    """
    if not HAS_GENAI:
        return -1, "Gemini library not found."
        
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        
        prompt = f"""
        You are a code reviewer with the persona: {mode}.
        Analyze the following Python code for complexity, style, and bad practices.
        
        Return the response EXACTLY in this format:
        Score: <Integer 0-100>
        Verdict: <One or two sentences of feedback in your persona>
        
        Code:
        {code}
        """
        
        response = model.generate_content(prompt)
        text = response.text
        
        # Parse Score
        score_match = re.search(r"Score:\s*(\d+)", text)
        if score_match:
            score = int(score_match.group(1))
        else:
            score = 50 # Default if parse fails
            
        # Parse Verdict
        verdict_match = re.search(r"Verdict:\s*(.*)", text, re.DOTALL)
        if verdict_match:
            verdict = verdict_match.group(1).strip()
        else:
            verdict = text # Fallback to full text if parse fails
            
        return score, verdict
        
    except Exception as e:
        console.print(f"[yellow]Gemini API warning: {e}. Falling back to local logic.[/yellow]")
        return -1, ""

def persist_result(filename: str, score: int, mode: str, method: str):
    """
    Saves the analysis result into a persistent SQLite database.
    Creates the table 'history' if it doesn't already exist.
    """
    try:
        # Locate DB in the parent directory (project root)
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rateMyCode_history.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Ensure schema exists (Added method column logic manually if needed, but keeping simple for now)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                filename TEXT,
                score INTEGER,
                mode TEXT
            )
        ''')
        # Note: We aren't storing 'method' in DB yet to avoid schema migration complexity for this task,
        # but we could add it later.
        
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
    Main Execution Flow
    """
    
    # 1. Argument Validation
    # Args: script, filepath, mode, voice_enabled, [api_key]
    if len(sys.argv) < 4:
        console.print("[red]Usage: python analyzer.py <filepath> <mode> <voice_enabled> [api_key][/red]")
        sys.exit(1)

    filepath = sys.argv[1]
    mode = sys.argv[2]
    voice_enabled = sys.argv[3]
    api_key = sys.argv[4] if len(sys.argv) > 4 else ""

    if not os.path.exists(filepath):
        console.print(f"[red]File not found: {filepath}[/red]")
        sys.exit(1)

    # 2. Read File Content
    with open(filepath, 'r') as f:
        code = f.read()

    # 3. Analyze
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        progress.add_task(description="Analyzing Code...", total=None)
        
        # Simulate processing time for UX effect
        import time
        time.sleep(0.5) 
        
        # Decide between Local AST or Remote LLM
        used_gemini = False
        if api_key and api_key.strip() != "" and "PASTE_YOUR" not in api_key:
            score, verdict_text = analyze_with_gemini(api_key, code, mode)
            if score != -1:
                depth = -1 # Not applicable for LLM
                used_gemini = True
            else:
                # Gemini failed, fallback
                depth = analyze_complexity(code)
                score = -1 # Will calculate below
        else:
            depth = analyze_complexity(code)
            score = -1

        # Fallback Calculation
        if not used_gemini:
            if depth == -1:
                # Re-check syntax error if we fell back
                depth = analyze_complexity(code)
            
            if depth == -1:
                console.print(f"[bold red]Syntax Error in {os.path.basename(filepath)}[/bold red]")
                verdict = "Your code is so broken I can't even analyze it."
                speak_feedback(verdict, voice_enabled)
                return
            
            # Local Scoring
            score = max(0, 100 - (depth * 20))
            verdict_text, color = get_feedback(score, mode)
        else:
            # Color logic for Gemini result
            if score >= 90: color = "green"
            elif score >= 70: color = "yellow"
            else: color = "red"

    # 5. Persist Data
    persist_result(os.path.basename(filepath), score, mode, "Gemini" if used_gemini else "AST")
    
    # 6. Display Results using Rich Table
    table = Table(title=f"RateMyCode: {os.path.basename(filepath)}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")
    table.add_column("Verdict", style=color)

    if used_gemini:
        table.add_row("Analysis Method", "Gemini AI", "Intelligent")
    else:
        table.add_row("Complexity (Depth)", str(depth), "High" if depth > 2 else "Acceptable")
    
    table.add_row("Quality Score", f"{score}/100", verdict_text)

    console.print(table)
    
    # 7. Audio Feedback (Threshold: < 80 score triggers speech)
    if score < 80:
        speak_feedback(verdict_text, voice_enabled)

if __name__ == "__main__":
    main()
