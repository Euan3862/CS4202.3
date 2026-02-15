import json
import sys

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


def direct(block, total_cache_lines, valid, tags):
    index = block % total_cache_lines
    tag = block // total_cache_lines

    if not valid[index]:
        valid[index] = 1
        tags[index] = tag
        return False
    elif tags[index] == tag:
        return True
    else:
        tags[index] = tag
        return False


def sim_cache(data, cache_count):
    trace_file = sys.argv[2]

    # L1
    cache_size_1 = data[0]["size"]
    line_size_1 = data[0]["line_size"]
    total_cache_lines_1 = cache_size_1 // line_size_1
    valid_1 = bytearray(total_cache_lines_1)
    tags_1 = [0] * total_cache_lines_1
    hit_count_1 = miss_count_1 = 0

    # L2 (optional)
    if cache_count >= 2:
        cache_size_2 = data[1]["size"]
        line_size_2 = data[1]["line_size"]
        total_cache_lines_2 = cache_size_2 // line_size_2
        valid_2 = bytearray(total_cache_lines_2)
        tags_2 = [0] * total_cache_lines_2
        hit_count_2 = miss_count_2 = 0

    # L3 (optional)
    if cache_count == 3:
        cache_size_3 = data[2]["size"]
        line_size_3 = data[2]["line_size"]
        total_cache_lines_3 = cache_size_3 // line_size_3
        valid_3 = bytearray(total_cache_lines_3)
        tags_3 = [0] * total_cache_lines_3
        hit_count_3 = miss_count_3 = 0

    try:
        with open(trace_file, "r") as tfile:
            for line in tfile:
                trace_line = line.split()
                if len(trace_line) < 4:
                    continue

                memory_address = int(trace_line[1], 16)
                memory_size = int(trace_line[3])

                start_block_1 = memory_address // line_size_1
                end_block_1 = (memory_address + memory_size - 1) // line_size_1

                for block1 in range(start_block_1, end_block_1 + 1):
                    l1_hit = direct(block1, total_cache_lines_1, valid_1, tags_1)
                    if l1_hit:
                        hit_count_1 += 1
                        continue

                    miss_count_1 += 1

                    if cache_count >= 2:
                        block_addr = block1 * line_size_1
                        block2 = block_addr // line_size_2
                        l2_hit = direct(block2, total_cache_lines_2, valid_2, tags_2)

                        if l2_hit:
                            hit_count_2 += 1
                        else:
                            miss_count_2 += 1

                            if cache_count == 3:
                                block_addr2 = block2 * line_size_2
                                block3 = block_addr2 // line_size_3
                                l3_hit = direct(block3, total_cache_lines_3, valid_3, tags_3)
                                if l3_hit:
                                    hit_count_3 += 1
                                else:
                                    miss_count_3 += 1

    except FileNotFoundError:
        print(f"Error: The file: {trace_file} was not found.", file=sys.stderr)
        sys.exit(1)

    if cache_count == 1:
        return hit_count_1, miss_count_1
    elif cache_count == 2:
        return hit_count_1, miss_count_1, hit_count_2, miss_count_2
    elif cache_count == 3:
        return hit_count_1, miss_count_1, hit_count_2, miss_count_2, hit_count_3, miss_count_3
    else:
        print("Error: this version supports only 1, 2, or 3 caches.", file=sys.stderr)
        sys.exit(1)


def json_results(hit_count_1, miss_count_1, data, cache_count,
                 hit_count_2=0, miss_count_2=0, hit_count_3=0, miss_count_3=0):
    results_1 = {
        "hits": hit_count_1,
        "misses": miss_count_1,
        "name": data[0]["name"]
    }

    caches_out = [results_1]

    if cache_count >= 2:
        results_2 = {
            "hits": hit_count_2,
            "misses": miss_count_2,
            "name": data[1]["name"]
        }
        caches_out.append(results_2)

    if cache_count == 3:
        results_3 = {
            "hits": hit_count_3,
            "misses": miss_count_3,
            "name": data[2]["name"]
        }
        caches_out.append(results_3)

    if cache_count == 1:
        main_memory_accesses = miss_count_1
    elif cache_count == 2:
        main_memory_accesses = miss_count_2
    else:
        main_memory_accesses = miss_count_3

    results = {
        "caches": caches_out,
        "main_memory_accesses": main_memory_accesses
    }

    print(json.dumps(results, indent=2), file=sys.stdout)


def main():
    data, cache_count = parse_config_file()

    if cache_count == 1:
        h1, m1 = sim_cache(data, cache_count)
        json_results(h1, m1, data, cache_count)
    elif cache_count == 2:
        h1, m1, h2, m2 = sim_cache(data, cache_count)
        json_results(h1, m1, data, cache_count, h2, m2)
    elif cache_count == 3:
        h1, m1, h2, m2, h3, m3 = sim_cache(data, cache_count)
        json_results(h1, m1, data, cache_count, h2, m2, h3, m3)
    else:
        print("Error: config must define 1, 2, or 3 caches.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
