
import os
import sys
import re
import ast
import json
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

class ScriptComplexityVisitor(ast.NodeVisitor):
    """
    Calculates complexity for top-level scripts that lack functions.
    Counts control flow statements.
    """
    def __init__(self):
        self.complexity = 1 # Base complexity
        
    def visit_If(self, node):
        self.complexity += 1
        self.generic_visit(node)
        
    def visit_For(self, node):
        self.complexity += 1
        self.generic_visit(node)
        
    def visit_While(self, node):
        self.complexity += 1
        self.generic_visit(node)
        
    def visit_Try(self, node):
        self.complexity += 1
        self.generic_visit(node)
        
    # We do NOT visit FunctionDef or ClassDef here because Radon handles those.
    # We only care about the global scope "spaghetti".

def analyze_complexity(code: str) -> int:
    """
    Calculates Cyclomatic Complexity using Radon (for functions/classes)
    AND custom AST traversal for top-level script logic.
    Returns the MAXIMUM complexity found (either a specific function or the script body).
    """
    max_complexity = 1
    
    try:
        # 1. Check Function/Class Complexity with Radon
        blocks = radon_cc.cc_visit(code)
        if blocks:
            max_complexity = max(block.complexity for block in blocks)
            
        # 2. Check Top-Level Script Complexity manually
        # This catches "spaghetti scripts" without functions
        tree = ast.parse(code)
        
        # We want to count complexity ONLY of top-level nodes, not double-count inside functions
        # So we iterate top-level nodes and only visit control flow ones
        script_visitor = ScriptComplexityVisitor()
        
        for node in tree.body:
             if isinstance(node, (ast.If, ast.For, ast.While, ast.Try)):
                 script_visitor.visit(node)
        
        script_complexity = script_visitor.complexity
        
        # logical max: is the script itself messier than its functions?
        return max(max_complexity, script_complexity)
        
    except SyntaxError:
        return -1
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
        
        prompt = f"""
        You are a code reviewer with the persona: {mode}.
        Analyze the following Python code for complexity, style, and bad practices.
        
        You must verify if the code is safe and follows best practices.
        
        Return the response AS A RAW JSON OBJECT. Do not use Markdown blocks.
        Format:
        {{
            "score": <Integer 0-100>,
            "verdict": "<One or two sentences of feedback>"
        }}

        Code:
        {code}
        """
        
        response = model.generate_content(prompt)
        text = response.text
        
        # Robust Parsing: Extract JSON structure using Regex
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            clean_json = json_match.group(0)
            data = json.loads(clean_json)
            return data.get("score", 50), data.get("verdict", "No verdict provided.")
        else:
            # Fallback if no JSON found
            return -1, "AI Response Malformed"
        
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

    try:
        with open(filepath, 'r') as f:
            code = f.read()
    except Exception as e:
        console.print(f"[red]Error reading file: {e}[/red]")
        return

    # Basic ignore
    if not code.strip():
        return

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        progress.add_task(description="Analyzing Code...", total=None)
        
        used_gemini = False
        score = -1
        depth = -1
        verdict_text = ""
        
        if api_key:
            score, verdict_text = analyze_with_gemini(api_key, code, mode)
            if score != -1:
                used_gemini = True

        if not used_gemini:
            depth = analyze_complexity(code)
            if depth == -1:
                # console.print(f"[bold red]Syntax Error or Analysis Failed in {os.path.basename(filepath)}[/bold red]")
                return
            
            # Score = 100 - (CC * 5). Min 0.
            score = max(0, 100 - (depth * 5))
            verdict_text, color = get_feedback(score, mode)
        else:
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
