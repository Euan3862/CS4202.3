import sys

def direct(block, total_cache_lines, valid, tags):
    index = block % total_cache_lines
    tag = block // total_cache_lines

    if not valid[index]:
        valid[index] = 1
        tags[index] = tag
        return False
    elif tags[index] == tag:
        return True
    else: # If cache line is valid, and not a matching tag then update cache line
        tags[index] = tag
        return False
    
def full_associative(block, total_cache_lines, valid, tags):
    cache_full = False
    tag = block
    for i in range(total_cache_lines):
        if not valid[i]:
            valid[i] = 1
            tags[i] = tag
            return False
        elif tags[i] == tag:
            return True
        else:
            cache_full = True
            break
    if (cache_full):
        round_robin(total_cache_lines, valid)
        full_associative(block, total_cache_lines, valid, tags)
    
        
def round_robin(total_cache_lines, valid): # Need to track last thrown out cache line!
    i = 0
    i = i % total_cache_lines
    valid[i] = False
    i += 1

def sim_cache(data, cache_count):
    trace_file = sys.argv[2]

    # L1 cache
    cache_size_1 = data[0]["size"]
    line_size_1 = data[0]["line_size"]
    total_cache_lines_1 = cache_size_1 // line_size_1
    valid_1 = bytearray(total_cache_lines_1)
    tags_1 = [0] * total_cache_lines_1
    hit_count_1 = miss_count_1 = 0
    kind_1 = data[0]["kind"]

    # L2 cache
    if cache_count >= 2:
        cache_size_2 = data[1]["size"]
        line_size_2 = data[1]["line_size"]
        total_cache_lines_2 = cache_size_2 // line_size_2
        valid_2 = bytearray(total_cache_lines_2)
        tags_2 = [0] * total_cache_lines_2
        hit_count_2 = miss_count_2 = 0
        kind_2 = data[1]["kind"]

    # L3 cace
    if cache_count == 3:
        cache_size_3 = data[2]["size"]
        line_size_3 = data[2]["line_size"]
        total_cache_lines_3 = cache_size_3 // line_size_3
        valid_3 = bytearray(total_cache_lines_3)
        tags_3 = [0] * total_cache_lines_3
        hit_count_3 = miss_count_3 = 0
        kind_3 = data[2]["kind"]

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

                    if (kind_1 == "direct"):
                        l1_hit = direct(block1, total_cache_lines_1, valid_1, tags_1)
                    elif (kind_1 == "full"):
                        l1_hit = full_associative(block1, total_cache_lines_1, valid_1, tags_1)
                    if l1_hit:
                        hit_count_1 += 1
                        continue

                    else: 
                        miss_count_1 += 1

                    if cache_count >= 2:
                        block_addr = block1 * line_size_1
                        block2 = block_addr // line_size_2

                        if (kind_1 == "direct"):
                            l2_hit = direct(block2, total_cache_lines_2, valid_2, tags_2)
                        elif (kind_1 == "full"):
                            l2_hit = full_associative(block2, total_cache_lines_2, valid_2, tags_2)

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
        print("Error; only 1, 2, or 3 caches supported.", file=sys.stderr)
        sys.exit(1)



