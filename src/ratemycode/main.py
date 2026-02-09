
import sys
import argparse
import os
from rich.console import Console
from .monitor import start_watching
from .utils import DatabaseManager
from .config import get_data_dir

console = Console()

def main():
    """
    Entry point for the rateMyCode application.
    """
    parser = argparse.ArgumentParser(description="RateMyCode: A real-time code quality assistant.")
    parser.add_argument("path", nargs="?", default=".", help="The directory to watch for code changes.")
    
    args = parser.parse_args()
    
    # 1. Security Check
    if os.path.exists(".env"):
         console.print("[bold yellow]WARNING: A .env file was found in your current directory.[/bold yellow]")
         console.print("[yellow]Ensure this file is in your .gitignore to prevent leaking your API Key![/yellow]")

    # 2. Add MANIFEST check warning if running from source without it? 
    # Not strictly necessary for runtime, but good for dev.

    # 3. Initialize Database Manager Singleton
    db_path = os.path.join(get_data_dir(), "rateMyCode_history.db")
    db_manager = DatabaseManager.initialize(db_path)

    try:
        start_watching(args.path)
    except KeyboardInterrupt:
        sys.exit(0)
    finally:
        # Shutdown DB thread gracefully
        db_manager.shutdown()

if __name__ == "__main__":
    main()
