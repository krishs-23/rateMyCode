
import os
import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .analyzer import analyze_file
from .config import load_config
from rich.console import Console

console = Console()

class CodeChangeHandler(FileSystemEventHandler):
    """
    Handles file system events for the watched directory.
    Implements debouncing to avoid multiple analysis triggers for a single save.
    """
    def __init__(self):
        self.last_modified = {}
        self.debounce_interval = 1.0 # Seconds
        config = load_config()
        # Load extensions from config, ensuring they have dots
        exts = config.get("supported_extensions", [".py", ".java", ".js", ".cpp"])
        self.supported_extensions = set(exts)

    def on_modified(self, event):
        if event.is_directory:
            return

        filename = event.src_path
        ext = os.path.splitext(filename)[1]
        
        if ext not in self.supported_extensions:
            return

        current_time = time.time()
        last_time = self.last_modified.get(filename, 0)

        if current_time - last_time > self.debounce_interval:
            self.last_modified[filename] = current_time
            # Run analysis in a separate thread to avoid blocking the watcher
            console.print(f"[cyan]Detected change in: {filename}[/cyan]")
            threading.Thread(target=analyze_file, args=(filename,), daemon=True).start()

def start_watching(path: str):
    """
    Starts the file watcher on the specified path.
    """
    if not os.path.exists(path):
        console.print(f"[red]Error: Directory '{path}' does not exist.[/red]")
        return

    event_handler = CodeChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    
    console.print(f"[green]RateMyCode is now watching: {os.path.abspath(path)}[/green]")
    console.print(f"[dim]Watching extensions: {', '.join(event_handler.supported_extensions)}[/dim]")
    console.print("[dim]Press Ctrl+C to stop.[/dim]")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    
    observer.join()
