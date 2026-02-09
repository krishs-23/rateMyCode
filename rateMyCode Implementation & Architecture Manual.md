# rateMyCode: Implementation & Architecture Manual
**Version:** 2.0
**Status:** In Production
**Target System:** Pure Python CLI Tool

## 1. Project Overview
**rateMyCode** is a local development tool designed to enforce code quality standards through automated analysis and "gamified" feedback. It utilizes a **Pure Python** architecture for maximum portability and maintainability.

**Core Functionality:**
1.  **Monitor:** Watches a specific directory for file changes in real-time using `watchdog`.
2.  **Analyze:** Parses modified code to calculate Cyclomatic Complexity (using `radon` and custom AST logic).
3.  **Persist:** Logs performance metrics to a local SQLite database for historical tracking.
4.  **Feedback:** Provides visual dashboards (CLI) and auditory critique (Text-to-Speech) based on configurable "personas."

## 2. System Architecture
The system follows a **Modular Monolith** pattern.

**Component A: The Monitor (`monitor.py`)**
*   **Role:** The file system watcher.
*   **Responsibility:**
    *   Uses `watchdog` to listen for `FileModifiedEvent`.
    *   Implements debouncing to prevent duplicate triggers.
    *   Spawns analysis tasks in separate threads.

**Component B: The Analyzer (`analyzer.py`)**
*   **Role:** The core logic engine.
*   **Responsibility:**
    *   **Hybrid Analysis:**
        *   **Local:** Uses `radon` for function/class complexity and custom AST traversal for top-level script complexity.
        *   **AI:** Uses Google Gemini API (if configured) for semantic analysis and "roasting".
    *   **Output:** Renders Rich tables to the console.

**Component C: The Feedback Engine (`utils.py`)**
*   **Role:** Multimedia output.
*   **Responsibility:**
    *   **TTS:** Runs `pyttsx3` in a separate process to ensure thread safety and strict isolation from the main loop.
    *   **Database:** Manages a persistent SQLite connection for logging scores.

## 3. Directory Structure Specification
```
rateMyCode/
├── pyproject.toml           [Project & Dependency Config]
├── README.md                [User Documentation]
├── src/
│   └── ratemycode/
│       ├── __init__.py
│       ├── main.py          [CLI Entry Point]
│       ├── monitor.py       [File Watcher]
│       ├── analyzer.py      [Analysis Logic]
│       ├── config.py        [Configuration Manager]
│       └── utils.py         [Shared Utilities (TTS, DB)]
├── tests/                   [Unit Tests]
└── venv/                    [Virtual Environment]
```

## 4. Configuration Specification
Configuration is managed via `config.py` using `appdirs`.
*   **Location:** `~/.config/rateMyCode/config.json` (OS dependent).
*   **Environment Variables:** `GEMINI_API_KEY` can be set via `.env` or system environment.

## 5. Implementation Details

### Complexity Analysis
*   **Library:** `radon`
*   **Top-Level Support:** The analyzer manually traverses the AST of top-level scripts to ensure "spaghetti code" outside of functions is caught and penalized.

### AI Integration
*   **Model:** Google Gemini
*   **Format:** JSON Mode. The system strictly parses JSON outputs and includes fallback mechanisms if the LLM hallucinates formats.

### Concurrency
*   **File Watching:** runs on a background thread (`watchdog.observers.Observer`).
*   **Analysis:** runs on a dedicated thread per file event.
*   **TTS:** runs in a `multiprocessing.Process` to prevent GIL blocking and OS-level audio crashes.

## 6. Build & Deployment
*   **Build System:** `setuptools` (via `pyproject.toml`).
*   **Installation:** `pip install .`
