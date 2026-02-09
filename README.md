# rateMyCode 🧐🔥

**rateMyCode** is a casual and unfiltered (or strictly professional) **Real-Time Code Quality Assistant** that lives in your terminal.

It matches your project directory while you code, and the moment you save a file, it:
1.  **Analyzes** the complexity of your code (Cyclomatic Complexity).
2.  **Rates** your code quality on a scale of 0-100.
3.  **Roasts** you (or compliments you) using different AI personas.
4.  **Speaks** the feedback out loud using Text-to-Speech (TTS).

---

## 🚀 Features

*   **Real-Time Monitoring**: Instantly reacts to file saves (`Ctrl+S`) using `watchdog`.
*   **Hybrid Analysis Engine**:
    *   **Local Logic**: Uses `radon` (and custom AST traversal) to calculate Cyclomatic Complexity locally and instantly.
    *   **Gemini AI Integration**: Uses Google's Gemini API for deep, semantic code reviews and custom roasts.
*   **Multiple Personas**:
    *   👹 **SAVAGE**: Ruthlessly mocks bad code. ("My CPU hurts just looking at this.")
    *   👔 **PROFESSIONAL**: Constructive, corporate-style feedback.
    *   🥺 **GENTLE**: Encouraging and kind for beginners.
*   **Voice Feedback**: Reads the verdict aloud asynchronously so you can hear your failure (or success) without UI freezes.
*   **Database Tracking**: Logs every analysis to a local SQLite database (`rateMyCode_history.db`) to track your improvement over time.
*   **Flexible CLI**: Run it from anywhere to monitor any project on your system.

---

## 🛠 Prerequisites

*   **Python 3.8+**
*   **Google Gemini API Key** (Optional, for AI features)

---

## 📥 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/krishs-23/rateMyCode.git
cd rateMyCode
```

### 2. Install
We recommend installing in a virtual environment:
```bash
# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install the package
pip install .
```

---

## 💻 Usage

### Activate the Environment
If you haven't already:
```bash
source venv/bin/activate
```

### Monitor Current Directory
To watch the folder you are currently in:
```bash
ratemycode
```

### Monitor a Specific Project
To watch an external project folder:
```bash
ratemycode /path/to/my/awesome/project
```

### Configuration
Configuration is stored in your user configuration directory (e.g., `~/.config/rateMyCode/config.json` on macOS/Linux).
The first time you run the tool, it will use defaults. You can create/edit the file to customize:

```json
{
    "mode": "SAVAGE",
    "voice_enabled": true,
    "max_complexity": 3,
    "gemini_api_key": "YOUR_KEY_HERE",
    "supported_extensions": [".py", ".java", ".js", ".cpp", ".ts", ".go", ".rs"]
}
```

**Security Note:** You can also control the API key via environment variable:
```bash
export GEMINI_API_KEY="your_api_key_here"
```
> **Warning**: Do not commit a `.env` file containing your API key to a public repository!

---

## 🧠 How It Works

### The Architecture
The system uses a **Production-Ready Python** architecture:

1.  **The Watcher**: Uses `watchdog` to monitor file system events efficiently.
2.  **The Analyzer**:
    *   **Gemini Mode**: Sends code to the LLM for a full review (with JSON enforcement).
    *   **Local Mode**: Uses `radon` for function complexity + custom AST traversal for script complexity.
3.  **The Verdict**:
    *   **Console**: Renders pretty tables using `rich`.
    *   **Audio**: Uses `multiprocessing` to run TTS safely without crashing the main thread.
    *   **Database**: Uses a **Producer-Consumer Queue** to ensure SQLite writes are thread-safe.

### Directory Structure
```
rateMyCode/
├── src/            # Python Source Code
├── tests/          # Unit Tests
├── venv/           # Python Virtual Environment
└── pyproject.toml  # Project Config & Dependencies
```

---

## 🤝 Contributing
Pull requests are welcome! Feel free to add new Personas, support for more languages (C++, Rust, etc.), or better analysis metrics.

## 📄 License
MIT License.
