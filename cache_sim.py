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

def sim_cache(data, cache_count):
    trace_file = sys.argv[2]

    # L1 cache state.
    cache_size_1 = data[0]["size"]
    line_size_1 = data[0]["line_size"]
    total_cache_lines_1 = cache_size_1 // line_size_1
    valid_1 = bytearray(total_cache_lines_1) # Byte array for faster indexing and setting
    tags_1 = [0] * total_cache_lines_1
    hit_count_1 = miss_count_1 = 0
    kind_1 = data[0]["kind"]
    name_1 = data[0]["name"]
    rp_1 = data[0].get("replacement_policy", "rr")
    rr_state_1 = [0]
    lru_state_1 = {}
    lru_index_1 = [0]
    lfu_state_1 = {}

    use_n_way_1 = (kind_1 == "full" and "way" in name_1) or ("way" in kind_1)
    if use_n_way_1:
        way_src_1 = name_1 if "way" in name_1 else kind_1
        set_size_1 = int(way_src_1.split("way", maxsplit=1)[0])
        number_of_sets_1 = total_cache_lines_1 // set_size_1
        n_lru_index = [[0] for _ in range(number_of_sets_1)]
        n_lru_state_1 = [[0] * set_size_1 for _ in range(number_of_sets_1)]
        lfu_state_nway_1 = [[0] * set_size_1 for _ in range(number_of_sets_1)]
        n_rr_state_1 = [[0] for _ in range(number_of_sets_1)]
        inner_index = [[0] for _ in range(number_of_sets_1)]
        set_state_1 = [[-1] * set_size_1 for _ in range(number_of_sets_1)]
    
    

    # L2 cache state (if configured).
    if cache_count >= 2:
        cache_size_2 = data[1]["size"]
        line_size_2 = data[1]["line_size"]
        total_cache_lines_2 = cache_size_2 // line_size_2
        valid_2 = bytearray(total_cache_lines_2)
        tags_2 = [0] * total_cache_lines_2
        hit_count_2 = miss_count_2 = 0
        kind_2 = data[1]["kind"]
        name_2 = data[1]["name"]
        rp_2 = data[1].get("replacement_policy", "rr")
        rr_state_2 = [0]
        lru_state_2 = {}
        lru_index_2 = [0]
        lfu_state_2 = {}
        use_n_way_2 = (kind_2 == "full" and "way" in name_2) or ("way" in kind_2)
        if use_n_way_2:
            way_src_2 = name_2 if "way" in name_2 else kind_2
            set_size_2 = int(way_src_2.split("way", maxsplit=1)[0])
            number_of_sets_2 = total_cache_lines_2 // set_size_2
            n_lru_index_2 = [[0] for _ in range(number_of_sets_2)]
            n_lru_state_2 = [[0] * set_size_2 for _ in range(number_of_sets_2)]
            lfu_state_nway_2 = [[0] * set_size_2 for _ in range(number_of_sets_2)]
            n_rr_state_2 = [[0] for _ in range(number_of_sets_2)]
            inner_index_2 = [[0] for _ in range(number_of_sets_2)]
            set_state_2 = [[-1] * set_size_2 for _ in range(number_of_sets_2)]


    # L3 cache state (if configured).
    if cache_count == 3:
        cache_size_3 = data[2]["size"]
        line_size_3 = data[2]["line_size"]
        total_cache_lines_3 = cache_size_3 // line_size_3
        valid_3 = bytearray(total_cache_lines_3)
        tags_3 = [0] * total_cache_lines_3
        hit_count_3 = miss_count_3 = 0
        kind_3 = data[2]["kind"]
        name_3 = data[2]["name"]
        rp_3 = data[2].get("replacement_policy", "rr")
        rr_state_3 = [0]
        lru_state_3 = {}
        lru_index_3 = [0]
        lfu_state_3 = {}
        use_n_way_3 = (kind_3 == "full" and "way" in name_3) or ("way" in kind_3)
        if use_n_way_3:
            way_src_3 = name_3 if "way" in name_3 else kind_3
            set_size_3 = int(way_src_3.split("way", maxsplit=1)[0])
            number_of_sets_3 = total_cache_lines_3 // set_size_3
            n_lru_index_3 = [[0] for _ in range(number_of_sets_3)]
            n_lru_state_3 = [[0] * set_size_3 for _ in range(number_of_sets_3)]
            lfu_state_nway_3 = [[0] * set_size_3 for _ in range(number_of_sets_3)]
            n_rr_state_3 = [[0] for _ in range(number_of_sets_3)]
            inner_index_3 = [[0] for _ in range(number_of_sets_3)]
            set_state_3 = [[-1] * set_size_3 for _ in range(number_of_sets_3)]


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
                    start_block_1 = memory_address // line_size_1
                    end_block_1 = (memory_address + memory_size - 1) // line_size_1

                    for block1 in range(start_block_1, end_block_1 + 1):
                        if (kind_1 == "direct"):
                            l1_hit = direct(block1, total_cache_lines_1, valid_1, tags_1)
                        elif use_n_way_1:
                            l1_hit = n_set_associative(block1, total_cache_lines_1, valid_1, rp_1, n_rr_state_1, lfu_state_nway_1, set_size_1, number_of_sets_1, set_state_1, inner_index, n_lru_index, n_lru_state_1)
                        elif (kind_1 == "full"):
                            l1_hit = full_associative(block1, total_cache_lines_1, valid_1, tags_1, rp_1 ,rr_state_1, lru_state_1, lru_index_1, lfu_state_1)


                        if l1_hit:
                            hit_count_1 += 1
                            continue
                        else:
                            miss_count_1 += 1

                        if cache_count >= 2:
                            block_addr = block1 * line_size_1
                            block2 = block_addr // line_size_2

                            if (kind_2 == "direct"):
                                l2_hit = direct(block2, total_cache_lines_2, valid_2, tags_2)
                            elif use_n_way_2:
                                l2_hit = n_set_associative(block2, total_cache_lines_2, valid_2, rp_2, n_rr_state_2, lfu_state_nway_2, set_size_2, number_of_sets_2, set_state_2, inner_index_2, n_lru_index_2, n_lru_state_2)
                            elif (kind_2 == "full"):
                                l2_hit = full_associative(block2, total_cache_lines_2, valid_2, tags_2, rp_2,rr_state_2, lru_state_2, lru_index_2, lfu_state_2)

                            if l2_hit:
                                hit_count_2 += 1
                            else:
                                miss_count_2 += 1

                                if cache_count == 3:
                                    block_addr2 = block2 * line_size_2
                                    block3 = block_addr2 // line_size_3

                                    if (kind_3 == "direct"):
                                        l3_hit = direct(block3, total_cache_lines_3, valid_3, tags_3)
                                    elif use_n_way_3:
                                        l3_hit = n_set_associative(block3, total_cache_lines_3, valid_3, rp_3, n_rr_state_3, lfu_state_nway_3, set_size_3, number_of_sets_3, set_state_3, inner_index_3, n_lru_index_3, n_lru_state_3)
                                    elif (kind_3 == "full"):
                                        l3_hit = full_associative(block3, total_cache_lines_3, valid_3, tags_3, rp_3,rr_state_3, lru_state_3, lru_index_3, lfu_state_3)

                                    if l3_hit:
                                        hit_count_3 += 1
                                    else:
                                        miss_count_3 += 1
                    line = read_line()

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
        print("Error; only 1, 2, or 3 caches supported.", file=sys.stderr)
        sys.exit(1)
