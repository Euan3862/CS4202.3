import sys
import mmap

# Cache access helpers return True on hit, False on miss.

def direct(block, total_cache_lines, valid, tags):
    index = block % total_cache_lines
    tag = block // total_cache_lines

    if not valid[index]:     # If cache line is empty, then fill line and return a miss (False).
        valid[index] = 1
        tags[index] = tag
        return False
    elif tags[index] == tag: # If matching cache line exists, then return a hit (True).
        return True
    else:                    # If cache line is valid, and not a matching tag then update cache line and return a miss (False).
        tags[index] = tag
        return False

# For associative caches:
# - LRU/LFU metadata is updated on both hits and fills.
# - LFU/LRU ties are broken by smallest line index.
def full_associative(block, total_cache_lines, valid, tags, rp, rr_state, lru_state, lru_index, lfu_state):
    tag = block
    for i in range(total_cache_lines):  # Scan all cache lines for a hit.
        if (tags[i] == tag and valid[i]):
            if (rp == "lru"):
                lru_state[i] = lru_index[0]
                lru_index[0] += 1
            elif (rp == "lfu"):
                lfu_state[i] += 1
            return True

    for i in range(total_cache_lines):  # If no hit found, then search for an empty cache line to fill and return a miss
        if not valid[i]:
            valid[i] = 1
            tags[i] = tag
            if (rp == "lru"):
                lru_state[i] = lru_index[0]
                lru_index[0] += 1
            elif (rp == "lfu"):
                lfu_state[i] = 1
            return False

    if (rp == "lru"):
        victim = lru(lru_state)
        lru_state[victim] = lru_index[0]
        lru_index[0] += 1
    elif (rp == "lfu"):
        victim = lfu(lfu_state)
        lfu_state[victim] = 1
    elif (rp == "rr"): # Resort to round robin if no replacement policy provided
        victim = round_robin(total_cache_lines, rr_state)
    valid[victim] = 1
    tags[victim] = tag
 
    return False


def n_set_associative(block, total_cache_lines, valid, rp, rr_state, lfu_state, n_ways, number_of_sets, set_state, inner_index, n_lru_index, n_lru_state):
    # Map block -> set and tag.
    index = block % number_of_sets
    tag = block // number_of_sets
    used_ways = inner_index[index][0]

    for way in range(used_ways):
        if set_state[index][way] == tag:
            if rp == "lru":
                n_lru_state[index][way] = n_lru_index[index][0]
                n_lru_index[index][0] += 1
            elif rp == "lfu":
                lfu_state[index][way] += 1
            return True

    # Fill empty way before applying replacement.
    if used_ways < n_ways:
        valid[index] = 1
        set_state[index][used_ways] = tag
        if rp == "lru":
            n_lru_state[index][used_ways] = n_lru_index[index][0]
            n_lru_index[index][0] += 1
        elif rp == "lfu":
            lfu_state[index][used_ways] = 1
        inner_index[index][0] += 1
        return False

    # Set is full: choose victim by policy.
    if rp == "lru":
        victim = n_lru_state[index].index(min(n_lru_state[index]))
        n_lru_state[index][victim] = n_lru_index[index][0]
        n_lru_index[index][0] += 1
    elif rp == "lfu":
        victim = lfu_state[index].index(min(lfu_state[index]))
        lfu_state[index][victim] = 1
    else:  # Resort to round robin if no replacement policy provided.
        victim = round_robin(n_ways, rr_state[index])

    set_state[index][victim] = tag
    return False

    
def round_robin(total_cache_lines, rr_state):
    # Per-cache or per-set RR pointer.
    victim = rr_state[0]
    rr_state[0] = (rr_state[0] + 1) % total_cache_lines
    return victim

def lru(lru_state):
    # Single-pass min with stable tie-break (smallest index wins).
    victim = None
    best = None
    for index, value in lru_state.items():
        if best is None or value < best or (value == best and index < victim):
            best = value
            victim = index
    return victim

def lfu(lfu_list):
    # Single-pass min with stable tie-break (smallest index wins).
    victim = None
    best = None
    for index, value in lfu_list.items():
        if best is None or value < best or (value == best and index < victim):
            best = value
            victim = index
    return victim

def build_cache(cache_config):
    cache_size = cache_config["size"]
    line_size = cache_config["line_size"]
    total_lines = cache_size // line_size
    kind = cache_config["kind"]
    replacement_policy = cache_config.get("replacement_policy", "rr")

    cache_state = {
        "name": cache_config["name"],
        "kind": kind,
        "rp": replacement_policy,
        "line_size": line_size,
        "lines": total_lines,
        "hits": 0,
        "misses": 0,
    }

    if kind == "direct":
        cache_state["valid"] = bytearray(total_lines)
        cache_state["tags"] = [0] * total_lines
        return cache_state

    if "way" in kind:
        ways = int(kind.split("way", maxsplit=1)[0])
        set_count = total_lines // ways

        cache_state["ways"] = ways
        cache_state["set_count"] = set_count
        cache_state["set_valid"] = bytearray(set_count)
        cache_state["set_tags"] = [[-1] * ways for _ in range(set_count)]
        cache_state["used_ways"] = [[0] for _ in range(set_count)]
        cache_state["set_rr_state"] = [[0] for _ in range(set_count)]

        if replacement_policy == "lru":
            cache_state["set_lru_index"] = [[0] for _ in range(set_count)]
            cache_state["set_lru_state"] = [[0] * ways for _ in range(set_count)]
        elif replacement_policy == "lfu":
            cache_state["set_lfu_state"] = [[0] * ways for _ in range(set_count)]
        return cache_state

    cache_state["valid"] = bytearray(total_lines)
    cache_state["tags"] = [0] * total_lines
    cache_state["rr_state"] = [0]
    cache_state["lru_state"] = {}
    cache_state["lru_index"] = [0]
    cache_state["lfu_state"] = {}
    return cache_state

def access_cache(cache_state, block):
    kind = cache_state["kind"]
    rp = cache_state["rp"]

    if kind == "direct":
        return direct(
            block,
            cache_state["lines"],
            cache_state["valid"],
            cache_state["tags"],
        )

    if "way" in kind:
        return n_set_associative(
            block,
            cache_state["lines"],
            cache_state["set_valid"],
            rp,
            cache_state["set_rr_state"],
            cache_state.get("set_lfu_state", []),
            cache_state["ways"],
            cache_state["set_count"],
            cache_state["set_tags"],
            cache_state["used_ways"],
            cache_state.get("set_lru_index", []),
            cache_state.get("set_lru_state", []),
        )

    return full_associative(
        block,
        cache_state["lines"],
        cache_state["valid"],
        cache_state["tags"],
        rp,
        cache_state["rr_state"],
        cache_state["lru_state"],
        cache_state["lru_index"],
        cache_state["lfu_state"],
    )

def sim_cache(data, cache_count):
    trace_file = sys.argv[2]
    caches = [build_cache(cache_config) for cache_config in data]
    line_sizes = [cache_state["line_size"] for cache_state in caches]
    total_cache_count = len(caches)
    main_memory_accesses = 0


    try:
        with open(trace_file, "rb") as tfile:
            with mmap.mmap(tfile.fileno(), 0, access=mmap.ACCESS_READ) as trace_map:
                parse_int = int
                read_line = trace_map.readline
                line = read_line()
                while line:
                    # Keep split-based parsing: for this trace format, PyPy/CPython's
                    # C-level bytes.split is faster than manual Python byte slicing.
                    trace_line = line.split(maxsplit=3)

                    memory_address = parse_int(trace_line[1], 16)
                    memory_size = parse_int(trace_line[3])

                    # Handle accesses that span multiple cache lines.
                    start_block_l1 = memory_address // line_sizes[0]
                    end_block_l1 = (memory_address + memory_size - 1) // line_sizes[0]

                    for block_l1 in range(start_block_l1, end_block_l1 + 1):
                        current_block = block_l1

                        for level in range(total_cache_count):
                            cache_state = caches[level]
                            cache_hit = access_cache(cache_state, current_block)

                            if cache_hit:
                                cache_state["hits"] += 1
                                break

                            cache_state["misses"] += 1
                            if level == total_cache_count - 1:
                                main_memory_accesses += 1
                                break

                            next_level = level + 1
                            current_block = (
                                (current_block * line_sizes[level]) // line_sizes[next_level]
                            )
                    line = read_line()

    except FileNotFoundError:
        print(f"Error: The file: {trace_file} was not found.", file=sys.stderr)
        sys.exit(1)

    return caches, main_memory_accesses
