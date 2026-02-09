# rateMyCode 🧐🔥

**rateMyCode** is a casual and unfiltered (or strictly professional) **Real-Time Code Quality Assistant** that lives in your terminal. 

It watches your project directory while you code, and the moment you save a file, it:
1.  **Analyzes** the complexity of your code (Big-O loops).
2.  **Rates** your code quality on a scale of 0-100.
3.  **Roasts** you (or compliments you) using different AI personas.
4.  **Speaks** the feedback out loud using Text-to-Speech (TTS).

---

## 🚀 Features

*   **Real-Time Monitoring**: Instantly reacts to file saves (`Ctrl+S`).
*   **Hybrid Analysis Engine**: 
    *   **Local AST Logic**: Uses Abstract Syntax Trees to calculate nesting depth (O(n), O(n^2), etc.) locally and instantly.
    *   **Gemini AI Integration**: Uses Google's Gemini API for deep, semantic code reviews and custom roasts.
*   **Multiple Personas**:
    *   👹 **SAVAGE**: Ruthlessly mocks bad code. ("My CPU hurts just looking at this.")
    *   👔 **PROFESSIONAL**: Constructive, corporate-style feedback.
    *   🥺 **GENTLE**: Encouraging and kind for beginners.
*   **Voice Feedback**: Reads the verdict aloud so you can hear your failure (or success).
*   **Database Tracking**: Logs every analysis to a local SQLite database (`rateMyCode_history.db`) to track your improvement over time.
*   **Flexible CLI**: Run it from anywhere to monitor any project on your system.

---

## 🛠 Prerequisites

*   **Java 17+** (For the main controller)
*   **Python 3.8+** (For the analysis engine)
*   **Google Gemini API Key** (Optional, for AI features)

---

## 📥 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/krishs-23/rateMyCode.git
cd rateMyCode
```

### 2. Configure Settings
Copy the template configuration file:
```bash
cp config.properties.template config.properties
```

Open `config.properties` and edit the settings:
```properties
mode=SAVAGE                  # Choose: SAVAGE, PROFESSIONAL, GENTLE
voice_enabled=true           # Enable Text-to-Speech
gemini_api_key=YOUR_KEY_HERE # (Optional) Get from aistudio.google.com
```
> **Note**: If you don't provide an API Key, the tool will automatically fall back to the local logic (counting nested loops).

### 3. Run the Installer
This script sets up the Python virtual environment, installs dependencies, and compiles the Java application.
```bash
./install.sh
```

---

## 💻 Usage

### Monitor Current Directory
To watch the folder you are currently in:
```bash
./ratemycode .
```

### Monitor a Specific Project
To watch an external project folder:
```bash
./ratemycode /path/to/my/awesome/project
```

### Global Installation (Optional)
To run `ratemycode` from anywhere without typing `./`, add it to your PATH:
```bash
export PATH=$PATH:$(pwd)
```
Now you can just type `ratemycode .` in any terminal window!

---

## 🧠 How It Works

### The Architecture
The system uses an **Event-Driven Microservices** pattern (locally):

1.  **The Warden (Java)**: A lightweight daemon that uses `WatchService` to monitor file system events. When a file changes, it filters out noise and spawns a child process.
2.  **The Judge (Python)**: An ephemeral script that parses the code.
    *   If **Gemini API** is active, it sends the code to the LLM for a full review.
    *   If **Local Mode** is active, it uses Python's `ast` module to count loop nesting depth.
3.  **The Verdict**: The result is printed to the console using `rich` for pretty tables and spoken aloud using `pyttsx3`.

### Directory Structure
```
rateMyCode/
├── src/            # Java Source Code (The Controller)
├── engine/         # Python Source Code (The Logic)
├── venv/           # Python Virtual Environment
├── logs/           # System Logs
├── config.properties # User Configuration
└── rateMyCode_history.db # SQLite Database of your past scores
```

---

## 🤖 API Key Privacy
Your `gemini_api_key` is stored in `config.properties`. This file is **git-ignored** by default to prevent accidental leaks. Do not commit your `config.properties` file!

---

## 🤝 Contributing
Pull requests are welcome! Feel free to add new Personas, support for more languages (C++, Rust, etc.), or better analysis metrics.

## 📄 License
MIT License.
