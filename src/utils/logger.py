# src/utils/logger.py

class Log:
    """
    Console Logger with Colors using ANSI Escape Codes.
    Standard output wrapper for better visibility in VS Code terminal.
    """
    
    # ANSI Colors
    HEADER = '\033[95m'      # Purple
    BLUE = '\033[94m'        # Blue
    CYAN = '\033[96m'        # Cyan
    GREEN = '\033[92m'       # Green
    WARNING = '\033[93m'     # Yellow
    FAIL = '\033[91m'        # Red
    BOLD = '\033[1m'         # Bold
    UNDERLINE = '\033[4m'    # Underline
    RESET = '\033[0m'        # Reset to default

    @staticmethod
    def info(msg: str):
        """General information (White/Default)"""
        print(f"  [Info] {msg}")

    @staticmethod
    def trace(msg: str):
        """Lifecycle tracing (Cyan)"""
        print(f"{Log.CYAN}  [Trace] {msg}{Log.RESET}")

    @staticmethod
    def success(msg: str):
        """Success messages (Green)"""
        print(f"{Log.GREEN}[Success] {msg}{Log.RESET}")

    @staticmethod
    def warning(msg: str):
        """Warning messages (Yellow)"""
        print(f"{Log.WARNING}[Warning] {msg}{Log.RESET}")

    @staticmethod
    def error(msg: str):
        """Error messages (Red)"""
        print(f"{Log.FAIL}  [Error] {msg}{Log.RESET}")
    
    @staticmethod
    def performance(msg: str):
        """Performance metrics (Purple)"""
        print(f"{Log.HEADER}  [Perf]  {msg}{Log.RESET}")

    @staticmethod
    def section(msg: str):
        """Section Divider (Bold Blue)"""
        print(f"\n{Log.BLUE}{Log.BOLD}=== {msg} ==={Log.RESET}")