import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.net.URISyntaxException;
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
    private static String geminiApiKey; // Google Gemini API Key

    // --- Constants ---
    private static String installDir; // Path where the JAR/Class is located
    private static final String ENGINE_PATH = "engine/analyzer.py"; // Relative path to Python logic
    private static final String LOGS_DIR = "logs/"; // Directory for system logs
    private static String targetDir; // Directory to watch (from CLI arg)

    /**
     * Main System Loop
     * Initial startup sequence: Load Config -> Setup Dirs -> Start Watcher
     */
    public static void main(String[] args) {
        System.out.println("RateMyCode: Starting...");

        // 0. Resolve Paths
        resolveInstallationPath();

        // 1. Argument Parsing (Target Directory)
        if (args.length > 0) {
            targetDir = args[0];
        } else {
            targetDir = "."; // Default to current directory
        }

        // 2. Load User Configuration
        loadConfig();

        // 3. Ensure Project Structure Guidelines
        setupDirectories();

        // 4. Begin Infinite Monitoring Loop
        try {
            startWatchService();
        } catch (IOException | InterruptedException e) {
            System.err.println("Error in WatchService: " + e.getMessage());
            e.printStackTrace();
        }
    }

    private static void resolveInstallationPath() {
        try {
            // Find where this class is running from
            java.security.ProtectionDomain pd = RateMyCode.class.getProtectionDomain();
            java.security.CodeSource cs = pd.getCodeSource();
            java.net.URL location = cs.getLocation();

            File source = new File(location.toURI());

            if (source.isDirectory()) {
                // Running from class files (e.g. RateMyCode/src/ or RateMyCode/bin/)
                // We assume source is either the project root or a subdir of it
                // Heuristic: look for config.properties in thisdir or parent
                if (new File(source, "config.properties").exists()) {
                    installDir = source.getAbsolutePath();
                } else if (new File(source.getParent(), "config.properties").exists()) {
                    installDir = source.getParent();
                } else {
                    // Fallback: Assume we are in src/ and root is parent
                    installDir = source.getParent();
                }
            } else {
                // Running from JAR?
                // The source is the JAR file itself. Parent dir is the install dir.
                installDir = source.getParent();
            }

            System.out.println("Install Dir detected as: " + installDir);

        } catch (URISyntaxException e) {
            e.printStackTrace();
            installDir = ".";
        }
    }

    /**
     * Reads the 'config.properties' file from the INSTALLATION DIRECTORY.
     */
    private static void loadConfig() {
        Properties prop = new Properties();
        File configFile = new File(installDir, "config.properties");

        if (!configFile.exists()) {
            // Fallback: Check if config is in current directory (legacy mode)
            configFile = new File("config.properties");
        }

        try (FileInputStream fis = new FileInputStream(configFile)) {
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

            // Critical: Path to Python env (resolve relative to install dir)
            String rawPythonPath = prop.getProperty("python_path", "venv/bin/python");
            File pyFile = new File(rawPythonPath);
            if (!pyFile.isAbsolute()) {
                pythonPath = new File(installDir, rawPythonPath).getAbsolutePath();
            } else {
                pythonPath = rawPythonPath;
            }

            // API Key
            geminiApiKey = prop.getProperty("gemini_api_key", "");

            System.out.println(
                    "Configuration Loaded: Mode=" + mode + ", Voice=" + voiceEnabled + ", Python=" + pythonPath);

        } catch (IOException e) {
            System.err.println(
                    "Failed to load config.properties from " + configFile.getAbsolutePath() + ". Using defaults.");
            // Fallback Defaults
            mode = "PROFESSIONAL";
            voiceEnabled = false;
            maxComplexity = 3;
            pythonPath = "python"; // Hope it's in PATH
            geminiApiKey = "";
        }
    }

    /**
     * Ensures critical logs directory exists in the INSTALLATION DIRECTORY.
     */
    private static void setupDirectories() {
        createDirectoryIfNotExists(new File(installDir, LOGS_DIR).getAbsolutePath());
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
                // System.out.println("Created directory: " + dirPath); // Quiet logs
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
        Path path = Paths.get(targetDir).toAbsolutePath();

        // Sanity check
        if (!Files.exists(path)) {
            System.err.println("Target directory does not exist: " + path);
            return;
        }

        // Register for specific events: File Creation and Modification
        path.register(watchService, StandardWatchEventKinds.ENTRY_CREATE, StandardWatchEventKinds.ENTRY_MODIFY);
        System.out.println("Monitoring Target: " + path);

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
            // Resolve engine path relative to install dir
            File engineFile = new File(installDir, ENGINE_PATH);

            // Build the command: [python_executable] [script] [file_arg] [mode_arg]
            // [voice_arg] [api_key]
            ProcessBuilder pb = new ProcessBuilder(
                    pythonPath,
                    engineFile.getAbsolutePath(),
                    absoluteFilePath,
                    mode,
                    String.valueOf(voiceEnabled),
                    geminiApiKey);

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
