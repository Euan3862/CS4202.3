import json
import sys

def parse_config_file():
        if len(sys.argv) < 3:
            print("Usage: python cache_sim.py <config.json> <trace_file>")
            sys.exit(1)

        file_path = sys.argv[1]

        try:
            with open(file_path, 'r') as file:
                data = json.load(file)

        except FileNotFoundError:
            print("Error: The file:", file_path, "was not found.", file=sys.stderr)
            sys.exit(1)

        data = data["caches"]
        return data


def direct_mapped(data):
    hit_count = 0
    miss_count = 0

    cache_size = data[0].get("size")
    line_size = data[0].get("line_size")
    total_cache_lines = cache_size // line_size

    valid = bytearray(total_cache_lines) # Faster than an array for storing booleans
    tags = [0] * total_cache_lines

    trace_file = sys.argv[2]

    try:  # Deal with tracefiles line by line rather than storing then processing ie streaming
        with open(trace_file, 'r') as tfile:
            for line in tfile:
                trace_line = line.split()
                memory_address = int(trace_line[1], 16)
                memory_size = int(trace_line[3])

                start_block = memory_address // line_size
                end_block = (memory_address + memory_size - 1) // line_size

                for block in range(start_block, end_block + 1):
                    index = block % total_cache_lines  # Which cache line the block maps to
                    tag = block // total_cache_lines   # Tag identifies which block is in that line
                    
                    if valid[index] == 0: # If false
                        miss_count += 1
                        valid[index] = 1 # Set to true
                        tags[index] = tag

                    elif tag == tags[index]:
                        hit_count += 1
                    else:
                        tags[index] = tag
                        miss_count += 1

    except FileNotFoundError:
        print("Error: The file:", trace_file, "was not found.", file=sys.stderr)
        sys.exit(1)

    return hit_count, miss_count

def json_results(hit_count, miss_count, data):
    results = { 
        "caches": [
            {"hits": hit_count,
            "misses": miss_count,
            "name": data[0].get("name")}
        ],
        "main_memory_accesses": miss_count
    }
    # Need to add support for multiple caches!
    output = json.dumps(results, indent=2)
    print(output, file=sys.stdout)

def main():
    data = parse_config_file()
    hit_count, miss_count = direct_mapped(data)
    json_results(hit_count, miss_count, data)

if __name__=="__main__":
    main()