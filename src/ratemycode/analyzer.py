
import os
import sys
import re
import ast
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
import radon.complexity as radon_cc

try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

from .utils import get_feedback, persist_result, speak_feedback_async
from .config import load_config, get_data_dir

console = Console()

def analyze_complexity(code: str) -> int:
    """
    Calculates Cyclomatic Complexity using Radon.
    Returns the maximum complexity found in the code blocks.
    """
    try:
        # cc_visit returns a list of blocks (functions/classes) with their complexity
        blocks = radon_cc.cc_visit(code)
        if not blocks:
            # If no blocks (script only), allow it but maybe warn? 
            # For scripts, we can just return 1 as base complexity.
            return 1
        
        # Return the maximum complexity found
        return max(block.complexity for block in blocks)
    except Exception as e:
        console.print(f"[red]Error analyzing code complexity: {e}[/red]")
        return -1

def analyze_with_gemini(api_key: str, code: str, mode: str) -> tuple[int, str]:
    """
    Uses Gemini API to analyze the code with a structured JSON response.
    """
    if not HAS_GENAI:
        return -1, "Gemini library not found."
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        
        system_instruction = f"You are a code reviewer with the persona: {mode}. Analyze the code for complexity, style, and bad practices."
        
        prompt = f"""
        Analyze the following Python code.
        
        Return the response AS A RAW JSON OBJECT with no markdown formatting.
        The JSON object must have keys: "score" (integer 0-100) and "verdict" (string).

        Code:
        {code}
        """
        
        response = model.generate_content(prompt)
        text = response.text
        
        # Clean up potential markdown code blocks if the model ignores instruction
        text = text.replace("```json", "").replace("```", "").strip()
        
        import json
        data = json.loads(text)
        
        return data.get("score", 50), data.get("verdict", "No verdict provided.")
        
    except Exception as e:
        console.print(f"[yellow]Gemini API warning: {e}. Falling back to local logic.[/yellow]")
        return -1, ""

def analyze_file(filepath: str):
    """
    Main analysis function for a single file.
    """
    config = load_config()
    mode = config.get("mode", "PROFESSIONAL")
    voice_enabled = config.get("voice_enabled", False)
    api_key = config.get("gemini_api_key", "")

    if not os.path.exists(filepath):
        console.print(f"[red]File not found: {filepath}[/red]")
        return

    with open(filepath, 'r') as f:
        code = f.read()

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        progress.add_task(description="Analyzing Code...", total=None)
        
        # Determine method
        used_gemini = False
        score = -1
        depth = -1
        verdict_text = ""
        
        if api_key:
            score, verdict_text = analyze_with_gemini(api_key, code, mode)
            if score != -1:
                used_gemini = True

        if not used_gemini:
             # Fallback to Radon
            depth = analyze_complexity(code)
            if depth == -1:
                 # Syntax Error probably
                 console.print(f"[bold red]Syntax Error or Analysis Failed in {os.path.basename(filepath)}[/bold red]")
                 return
            
            # Simple scoring based on complexity
            # CC > 10 is generally considered bad.
            # Score = 100 - (CC * 5). Min 0.
            score = max(0, 100 - (depth * 5))
            verdict_text, color = get_feedback(score, mode)
        else:
             # Just get color for the verdict
             _, color = get_feedback(score, mode)

    # Persist
    db_path = os.path.join(get_data_dir(), "rateMyCode_history.db")
    persist_result(db_path, os.path.basename(filepath), score, mode, "Gemini" if used_gemini else "Radon")

    # Display
    table = Table(title=f"RateMyCode: {os.path.basename(filepath)}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")
    table.add_column("Verdict", style=color)

    if used_gemini:
        table.add_row("Analysis Method", "Gemini AI", "Intelligent")
    else:
        table.add_row("Complexity (CC)", str(depth), "High" if depth > 10 else "Acceptable")
    
    table.add_row("Quality Score", f"{score}/100", verdict_text)
    console.print(table)
    
    # TTS
    if score < 80:
        speak_feedback_async(verdict_text, voice_enabled)
