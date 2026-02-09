import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.nio.file.FileSystems;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardWatchEventKinds;
import java.nio.file.WatchEvent;
import java.nio.file.WatchKey;
import java.nio.file.WatchService;
import java.util.Properties;

/**
 * RateMyCode - The Warden
 * 
 * This class serves as the main entry point and "Warden" of the system.
 * It is responsible for:
 * 1. Loading system configuration.
 * 2. Setting up necessary directory structures.
 * 3. Monitoring the file system for code changes in real-time.
 * 4. Spawning a Python subprocess to analyze code quality when changes are
 * detected.
 */
public class RateMyCode {

    // --- Configuration Variables ---
    private static String mode; // Feedback Persona (SAVAGE, PROFESSIONAL, GENTLE)
    private static boolean voiceEnabled; // Toggle for Text-to-Speech
    private static int maxComplexity; // Threshold for loop nesting depth
    private static String pythonPath; // Path to the Python executable (in venv)

    // --- Constants ---
    private static final String ENGINE_PATH = "engine/analyzer.py"; // Relative path to Python logic
    private static final String DOCS_DIR = "docs/"; // Directory to watch
    private static final String LOGS_DIR = "logs/"; // Directory for system logs

    /**
     * Main System Loop
     * Initial startup sequence: Load Config -> Setup Dirs -> Start Watcher
     */
    public static void main(String[] args) {
        System.out.println("RateMyCode: Starting...");

        // 1. Load User Configuration
        loadConfig();

        // 2. Ensure Project Structure Guidelines
        setupDirectories();

        // 3. Begin Infinite Monitoring Loop
        try {
            startWatchService();
        } catch (IOException | InterruptedException e) {
            System.err.println("Error in WatchService: " + e.getMessage());
            e.printStackTrace();
        }
    }

    /**
     * Reads the 'config.properties' file to populate system settings.
     * RAM-loads values like Mode and Voice Toggle.
     * Falls back to safe defaults if the file is missing or corrupt.
     */
    private static void loadConfig() {
        Properties prop = new Properties();
        try (FileInputStream fis = new FileInputStream("config.properties")) {
            prop.load(fis);

            // Read string property, default to PROFESSIONAL if logic fails
            mode = prop.getProperty("mode", "PROFESSIONAL");

            // Parse boolean flag
            voiceEnabled = Boolean.parseBoolean(prop.getProperty("voice_enabled", "false"));

            // Parse integer complexity limit
            try {
                maxComplexity = Integer.parseInt(prop.getProperty("max_complexity", "3"));
            } catch (NumberFormatException e) {
                maxComplexity = 3; // Default safety net
            }

            // Critical: Path to Python env
            pythonPath = prop.getProperty("python_path", "venv/bin/python");

            System.out.println(
                    "Configuration Loaded: Mode=" + mode + ", Voice=" + voiceEnabled + ", Python=" + pythonPath);

        } catch (IOException e) {
            System.err.println("Failed to load config.properties. Using defaults.");
            // Fallback Defaults
            mode = "PROFESSIONAL";
            voiceEnabled = false;
            maxComplexity = 3;
            pythonPath = "python";
        }
    }

    /**
     * Ensures critical directories exist on disk before operation begins.
     * Prevents IOErrors later during runtime to ensure robustness.
     */
    private static void setupDirectories() {
        createDirectoryIfNotExists(DOCS_DIR);
        createDirectoryIfNotExists(LOGS_DIR);
    }

    /**
     * Helper Method: Creates a directory if it doesn't exist.
     * 
     * @param dirPath The relative or absolute path to create.
     */
    private static void createDirectoryIfNotExists(String dirPath) {
        File dir = new File(dirPath);
        if (!dir.exists()) {
            if (dir.mkdirs()) {
                System.out.println("Created directory: " + dirPath);
            } else {
                System.err.println("Failed to create directory: " + dirPath);
            }
        }
    }

    /**
     * THE EVENT LOOP
     * Uses Java NIO WatchService to hook into OS file system events.
     * This method blocks indefinitely (while(true)) waiting for file changes.
     */
    private static void startWatchService() throws IOException, InterruptedException {
        // Initialize the watchers
        WatchService watchService = FileSystems.getDefault().newWatchService();
        Path path = Paths.get(DOCS_DIR);

        // Sanity check
        if (!Files.exists(path)) {
            System.err.println("Directory docs/ does not exist!");
            return;
        }

        // Register for specific events: File Creation and Modification
        path.register(watchService, StandardWatchEventKinds.ENTRY_CREATE, StandardWatchEventKinds.ENTRY_MODIFY);
        System.out.println("Monitoring: " + path.toAbsolutePath());

        // Infinite Loop
        while (true) {
            WatchKey key = watchService.take(); // Block until an event occurs

            for (WatchEvent<?> event : key.pollEvents()) {
                WatchEvent.Kind<?> kind = event.kind();

                // Handle overflow (too many events at once) - safely ignore
                if (kind == StandardWatchEventKinds.OVERFLOW) {
                    continue;
                }

                // Get the file name from the event context
                Path filename = (Path) event.context();
                String fileNameStr = filename.toString();

                // Filter Logic: Ignore system files (like .DS_Store) and temp files
                if (fileNameStr.startsWith(".") || fileNameStr.endsWith(".tmp") || fileNameStr.endsWith("~")) {
                    continue;
                }

                // Only act on supported code files
                if (isValidCodeFile(fileNameStr)) {
                    System.out.println("Detected change in: " + fileNameStr);

                    // Simple Debounce: Sleep briefly to ensure file write is complete before
                    // reading
                    Thread.sleep(100);

                    // Trigger the Python Analysis Engine
                    runAnalyzer(path.resolve(filename).toAbsolutePath().toString());
                }
            }

            // Reset the key to receive further events. If reset fails, loop exits.
            boolean valid = key.reset();
            if (!valid) {
                break;
            }
        }
    }

    /**
     * Validation Logic
     * Checks if the modified file is a source code file we care about.
     */
    private static boolean isValidCodeFile(String fileName) {
        return fileName.endsWith(".py") || fileName.endsWith(".java") || fileName.endsWith(".js")
                || fileName.endsWith(".cpp");
    }

    /**
     * Process Spawning
     * Constructs a command line execution to call the Python script.
     * Pipes the Python process I/O to the main Java console for visibility.
     * 
     * @param absoluteFilePath Full path to the modified file.
     */
    private static void runAnalyzer(String absoluteFilePath) {
        try {
            // Build the command: [python_executable] [script] [file_arg] [mode_arg]
            // [voice_arg]
            ProcessBuilder pb = new ProcessBuilder(
                    pythonPath,
                    ENGINE_PATH,
                    absoluteFilePath,
                    mode,
                    String.valueOf(voiceEnabled));

            // Redirect IO: This makes Python print statements appear in this terminal
            pb.inheritIO();

            // Execute
            Process process = pb.start();
            int exitCode = process.waitFor(); // Wait for script to finish

            // Error Checking
            if (exitCode != 0) {
                System.err.println("Analyzer exited with code: " + exitCode);
            }

        } catch (IOException | InterruptedException e) {
            System.err.println("Failed to run analyzer: " + e.getMessage());
            e.printStackTrace();
        }
    }
}
