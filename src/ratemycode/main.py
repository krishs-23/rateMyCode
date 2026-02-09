
import sys
import argparse
from .monitor import start_watching

def main():
    """
    Entry point for the rateMyCode application.
    """
    parser = argparse.ArgumentParser(description="RateMyCode: A real-time code quality assistant.")
    parser.add_argument("path", nargs="?", default=".", help="The directory to watch for code changes.")
    
    args = parser.parse_args()
    
    try:
        start_watching(args.path)
    except KeyboardInterrupt:
        sys.exit(0)

if __name__ == "__main__":
    main()
