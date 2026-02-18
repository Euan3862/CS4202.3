import sys
import json

def parse_config_file():
    if len(sys.argv) < 3:
        print("Usage: python cache_sim.py <config.json> <trace_file>")
        sys.exit(1)

    file_path = sys.argv[1]
    try:
        with open(file_path, "r") as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"Error: The file: {file_path} was not found.", file=sys.stderr)
        sys.exit(1)

    caches = data["caches"]
    cache_count = len(caches)
    return caches, cache_count