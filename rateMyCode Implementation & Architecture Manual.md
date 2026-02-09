## rateMyCode: Implementation & Architecture Manual  
**Version:** 1.0  
**Status:** Ready for Development  
**Target System:** Hybrid Java/Python CLI Tool  
  
## 1. Project Overview  
**rateMyCode** is a local development tool designed to enforce code quality standards through automated analysis and "gamified" feedback. It utilizes a hybrid architecture where **Java** handles system-level monitoring (reliability/performance) and **Python** handles logic, AI analysis, and multimedia feedback.  
**Core Functionality:**  
1. **Monitor:** Watches a specific directory for file changes in real-time.  
2. **Analyze:** Parses modified code to calculate Algorithmic Complexity (Big O notation estimation).  
3. **Persist:** Logs performance metrics to a local database for historical tracking.  
4. **Feedback:** Provides visual dashboards (CLI) and auditory critique (Text-to-Speech) based on configurable "personas."  
  
## 2. System Architecture  
The system follows an **Event-Driven Microservices** pattern, implemented locally via process spawning.  
**Component A: The Warden (Java Controller)**  
* **Role:** The daemon process that runs indefinitely.  
* **Responsibility:**  
    * Reads configuration settings on startup.  
    * Establishes a file system watch on the target directory.  
    * Filters events (ignores temporary files, focuses on .py, .java, .js).  
    * Spawns the Python subprocess when a relevant file is modified.  
    * Pipes the Python output back to the main terminal.  
**Component B: The Judge (Python Engine)**  
* **Role:** The ephemeral execution script (runs once per file save).  
* **Responsibility:**  
    * Receives file path and configuration arguments from Java.  
    * Performs Abstract Syntax Tree (AST) analysis.  
    * Calculates a "Quality Score" (0-100).  
    * Writes results to the SQLite database.  
    * Generates the User Interface (UI) and Audio (TTS).  
  
## 3. Directory Structure Specification  
Strict adherence to this structure is required for relative pathing to function correctly.  
Plaintext  
##   
##   
##   
rateMyCode/                  [Root Directory]  
├── config.properties        [User Configuration File]  
├── .gitignore               [Git Exclusion Rules]  
├── docs/                    [Target Watch Directory - User Code Goes Here]  
├── logs/                    [System Logs Directory - Auto-Generated]  
├── src/                     [Java Source Code]  
│   └── RateMyCode.java      [Main Controller Class]  
├── engine/                  [Python Source Code]  
│   ├── analyzer.py          [Core Logic Script]  
│   └── requirements.txt     [Python Dependencies List]  
└── venv/                    [Python Virtual Environment - Auto-Generated]  
  
## 4. Configuration Specification (config.properties)  
The system must be configurable via a key-value properties file located in the root.  
**Required Keys:**  
1. **mode**: Defines the "Persona" of the feedback.  
    * *Values:* SAVAGE (Aggressive roasting), PROFESSIONAL (Corporate feedback), GENTLE (Encouraging).  
2. **voice_enabled**: Toggle for Text-to-Speech.  
    * *Values:* true, false.  
3. **max_complexity**: The threshold for nested loops before a warning is triggered.  
    * *Values:* Integer (e.g., 3 implies O(n^3)).  
4. **python_path**: Absolute or relative path to the Python executable within the virtual environment.  
    * *Note:* Must support OS-specific paths (Windows Scripts/python.exe vs Mac/Linux bin/python).  
  
## 5. Implementation Details: The Java Controller  
**Class Name:** RateMyCode  
**Location:** src/RateMyCode.java  
**Logic Flow:**  
1. **Config Loading:**  
    * Instantiate a Properties object.  
    * Load config.properties via FileInputStream.  
    * Store the config values in local variables.  
2. **Directory Setup:**  
    * Check if the docs/ directory exists. If not, create it.  
    * Check if the logs/ directory exists. If not, create it.  
3. **WatchService Initialization:**  
    * Create a WatchService instance using the default FileSystem.  
    * Register the docs/ path for ENTRY_CREATE and ENTRY_MODIFY events.  
4. **The Event Loop:**  
    * Enter a while(true) loop.  
    * Poll for WatchKey events.  
    * **Filter Logic:** Iterate through events. Ignore system files (e.g., .DS_Store). Only proceed if the filename ends with a valid code extension.  
5. **Process Execution:**  
    * Construct a ProcessBuilder command list containing:  
        1. The python_path from config.  
        2. The relative path to engine/analyzer.py.  
        3. The absolute path of the modified file.  
        4. The mode from config.  
        5. The voice_enabled flag from config.  
    * Redirect ErrorStream to OutputStream (inherit IO) so Python errors appear in the Java terminal.  
    * Start the process and wait for it to complete (waitFor()).  
  
## 6. Implementation Details: The Python Engine  
**Script Name:** analyzer.py  
**Location:** engine/analyzer.py  
**Required Libraries:**  
* sys (Argument parsing)  
* ast (Abstract Syntax Tree parsing)  
* sqlite3 (Database interaction)  
* pyttsx3 (Text-to-Speech)  
* rich (Terminal UI formatting)  
**Logic Modules:**  
**A. Complexity Analysis Module**  
* **Input:** Raw code string.  
* **Method:** Parse code into an AST. Traverse the tree.  
* **Metric:** Count the maximum depth of nested For and While nodes.  
* **Output:** Integer representing depth (e.g., 1, 2, 3).  
* **Error Handling:** Catch SyntaxError if the code is unparseable (return -1).  
**B. Database Persistence Module**  
* **Database File:** rateMyCode_history.db (Created in root).  
* **Schema:** Table named history with columns:  
    * id (Auto-increment Primary Key)  
    * timestamp (DateTime)  
    * filename (Text)  
    * score (Integer)  
    * mode (Text)  
* **Action:** Insert a new row every time the script runs.  
**C. Scoring & Feedback Module**  
* **Scoring Formula:** Start with 100. Deduct X points for every level of nesting depth found. (Suggested: 20 points per level).  
* **Roast Logic:**  
    * If mode is SAVAGE: Use aggressive, informal language.  
    * If mode is PROFESSIONAL: Use formal, constructive language.  
    * Trigger conditions: Specific phrases for "Syntax Error", "High Complexity", or "Good Code".  
**D. User Interface (UI) Module**  
* Use the rich library to render:  
    * A Loading Bar (simulate processing time for effect).  
    * A "Report Card" Table showing: Metric Name, Value, and Verdict.  
    * Use color coding (Red for bad scores, Green for good).  
**E. Audio Module**  
* Initialize pyttsx3.  
* Set speech rate to ~170 words per minute.  
* **Logic:** Only speak the "Verdict" text if voice_enabled is true AND the Score is below a certain threshold (e.g., < 80).  
  
## 7. Build & Deployment Steps  
**Step 1: Python Environment**  
1. Initialize a virtual environment (venv) in the root.  
2. Activate the environment.  
3. Install the required packages (rich, pyttsx3).  
4. Generate a requirements.txt file in engine/.  
**Step 2: Java Compilation**  
1. Navigate to the root directory.  
2. Compile the source code: javac src/RateMyCode.java.  
**Step 3: Execution**  
1. Run the Java controller from the root to ensure relative paths align:  
    * Command: java -cp src RateMyCode  
  
## 8. Troubleshooting & Edge Cases  
1. **Path Issues:**  
    * *Problem:* Java cannot find the Python executable.  
    * *Fix:* Ensure config.properties points to the correct executable inside venv (Windows uses Scripts, Mac uses bin).  
2. **Database Locks:**  
    * *Problem:* sqlite3 error regarding locked database.  
    * *Fix:* Ensure the Python script closes the database connection (conn.close()) immediately after writing.  
3. **Audio Drivers:**  
    * *Problem:* pyttsx3 crashes on Linux/Mac.  
    * *Fix:* Wrap the audio call in a try/except block to prevent the main application from crashing if audio drivers are missing.  
  
## 9. Future Extensibility (Roadmap)  
* **LLM Integration:** Replace the hardcoded roast logic with an API call to Gemini/OpenAI for dynamic code reviews.  
* **Git Hooks:** Create a pre-commit hook that runs rateMyCode before allowing a commit.  
* **Web Dashboard:** Use the SQLite database to generate an HTML report of coding progress over time.  
