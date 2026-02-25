import mmap
import sys

"""
This program simulates a cache hierarchy with cache configurations set by a JSON config file and a memory trace to simulate. 
Each cache level gets its own access function built up front so that the returned function already knows its replacement policy and internal state.
This means that each trace lookup can just call it and get a hit or miss result quickly.
The simulator then reads the trace file lines in order, splits accesses that cross cache-line boundaries, checks L1 and then proceeds through lower levels until it hits, or otherwise
misses through to 'main memory', block numbers are converted between different line sizes, and lastly hit/miss counts per cache are recorded as well as the total of 
main-memory accesses for the simulated trace file.
"""


"""
This wrapper function runs once at cache level setup and sets up the cache's arrays/state,
whereas the inner access function is in the hot loop of the program and called a lot.

The wrapper function avoids repeated dictionary lookups within the hot loop and avoids
passing lots of state as extra function parameters every call which introduces a lot of overheads
and a real impact in program performance.
"""
def direct_accessor(total_cache_lines, valid_bits, tags):
    """
    Builds and returns a direct-mapped cache access function where the access function
    takes a block number and returns True if hit and false if a miss. The cache state is
    updated when needed, ie on cache fills/evictions.
    """
    def access(block):
        # As all counts are powers of two, block % lines can be done bitwise as block & (lines - 1) which provides speed improvements.
        line_index = block & (total_cache_lines - 1)
        tag_shift = total_cache_lines.bit_length() - 1
        tag = block >> tag_shift

        # If line has not been used yet, fill it and return a miss.
        if (not valid_bits[line_index]):
            valid_bits[line_index] = 1
            tags[line_index] = tag
            return False

        # If line is valid and tags match then return a hit.
        if (tags[line_index] == tag):
            return True

        # Otherwise, there is a cache line conflict so replace tag and return a miss.
        tags[line_index] = tag
        return False

    return access


# Fully associative wrapper function to keep cache setup out of the hot loop
def full_accessor(replacement_policy, total_cache_lines,tags, tag_to_line, free_lines):
    """
    The policy is chosen once here (rr/lru/lfu) and the matching access function is returned.
    This keeps the replacement policy branching out of the hot loop and prevents multiple checks.
    """
    if (replacement_policy == "rr"):
        round_robin_pointer = 0 # RR pointer that increments through all cache-lines then resets to the beginning.

        def access(block):
            nonlocal round_robin_pointer # Non local as it is the outer function rr pointer that should be updated

            hit_line = tag_to_line.get(block)
            if (hit_line is not None):
                return True

            # Fill unused lines first to avoid unnecessary replacements.
            if (free_lines):
                victim_line = free_lines.pop()
            else:
                # In case of a full cache, evict RR victim and increment pointer.
                victim_line = round_robin_pointer
                round_robin_pointer = (round_robin_pointer + 1) & (total_cache_lines - 1)

                # Ensure that old tags are deleted from dict to avoid false hits.
                old_tag = tags[victim_line]
                if tag_to_line.get(old_tag) == victim_line:
                    del tag_to_line[old_tag]

            tags[victim_line] = block # Update the victim line with new block
            tag_to_line[block] = victim_line # Update tag to line dict with the new line
            return False

        return access

    if replacement_policy == "lru":
        lru_state = [0] * total_cache_lines # lower value in lru state means older.
        lru_tick = 0

        def access(block):
            nonlocal lru_tick

            hit_line = tag_to_line.get(block)
            if (hit_line is not None): # If line is within tag to line, then return hit.
                # Hit: refresh recency and return.
                lru_state[hit_line] = lru_tick
                lru_tick += 1
                return True

            # If cache is not full, then fill the free lines first.
            if (free_lines):
                victim_line = free_lines.pop() 
            else:
                # Otherwise, cache is full so select the oldest line (smallest tick) and evict it.
                victim_line = 0
                oldest_tick = lru_state[0]
                for line_index in range(1, total_cache_lines):
                    line_tick = lru_state[line_index]
                    if line_tick < oldest_tick:
                        oldest_tick = line_tick
                        victim_line = line_index

                old_tag = tags[victim_line]
                if tag_to_line.get(old_tag) == victim_line:
                    del tag_to_line[old_tag]

            # Setting victim line to valid, entering the new tag, and incrementing lru counter.
            tags[victim_line] = block
            tag_to_line[block] = victim_line
            lru_state[victim_line] = lru_tick
            lru_tick += 1
            return False

        return access

    lfu_state = [0] * total_cache_lines # Maintains a count of frequency for cache line
    min_heap = [0] * total_cache_lines # Keeps track of the bottom of the heap ie heap[0] is the victim. This allows for o(1)
    heap_positions = [-1] * total_cache_lines # Maintain positions of lines in heap
    heap_size = 0

    def access(block):
        nonlocal heap_size

        hit_line = tag_to_line.get(block)
        if (hit_line is not None):
            # Hit increases frequency, then push line down if needed in min-heap.
            lfu_state[hit_line] += 1
            rebalance_lfu_heap_down(min_heap, heap_positions, lfu_state, heap_positions[hit_line], heap_size)
            return True

        if (free_lines):    # Fill free line and add it into LFU heap with count=1.
            victim_line = free_lines.pop()
            lfu_state[victim_line] = 1
            min_heap[heap_size] = victim_line
            heap_positions[victim_line] = heap_size
            heap_size += 1
            rebalance_lfu_heap_up(min_heap, heap_positions, lfu_state, heap_size - 1)
        else:
            # Cache is full; LFU victim is always the root of the heap (min_heap[0]).
            victim_line = min_heap[0]
            old_tag = tags[victim_line]

            if (tag_to_line.get(old_tag)) == victim_line:
                del tag_to_line[old_tag]

            # Reset frequency for new line.
            lfu_state[victim_line] = 1

            # Root element line id stays the same, so heap structure stays valid (Least used cache line)
        tags[victim_line] = block
        tag_to_line[block] = victim_line
        return False

    return access


# LFU tie break rule - If two lines have the same frequency, evict the line with smaller index first.
def is_lower_lfu_priority(access_counts, left_line, right_line):
    left_count = access_counts[left_line]
    right_count = access_counts[right_line]
    return left_count < right_count or (left_count == right_count and left_line < right_line) # Tie break case where lowest index is chosen


# Restores order of heap after increasing/decreasing a node priority by moving it upward.
# Keeps a separate heap_positions array so a line can be found/updated in O(1).
def rebalance_lfu_heap_up(min_heap, heap_positions, access_counts, node_index):
    while (node_index):
        # Parent of i in a binary heap stored in an array is (i - 1) // 2.
        parent_index = (node_index - 1) >> 1
        node_line = min_heap[node_index]
        parent_line = min_heap[parent_index]

        if (not is_lower_lfu_priority(access_counts, node_line, parent_line)): # Stop once heap order is correct.
            return

        # Swap child and parent to move the lower-priority (evict-first) line upward.
        min_heap[node_index] = parent_line
        min_heap[parent_index] = node_line

        # Keep reverse lookup positions in sync with the heap swaps.
        heap_positions[node_line] = parent_index
        heap_positions[parent_line] = node_index
        node_index = parent_index


# Restores the heap order by pushing a node downwards.
# This is used after LFU hits (count increase) and after root replacement.
def rebalance_lfu_heap_down(min_heap, heap_positions, access_counts, node_index, heap_size):
    while (True):
        left_child = (node_index << 1) + 1  # Left child index is 2*i + 1.
        if (left_child >= heap_size): # Left child is not part of the heap
            return

        right_child = left_child + 1
        smaller_child = left_child

        # Choose child with lower LFU priority (higher chance of being evicted) to preserve min-heap property.
        if (heap_size > right_child and is_lower_lfu_priority(access_counts, min_heap[right_child], min_heap[left_child])):
            smaller_child = right_child

        node_line = min_heap[node_index]
        child_line = min_heap[smaller_child]

        #Stop when current node is already <= best child by LFU ordering.
        if (not is_lower_lfu_priority(access_counts, child_line, node_line)):
            return

        #Swap node with best child and continue downwards.
        min_heap[node_index] = child_line
        min_heap[smaller_child] = node_line
        heap_positions[child_line] = node_index
        heap_positions[node_line] = smaller_child
        node_index = smaller_child


# n-way set-associative wrapper for rr/lru/lfu.
def set_accessor(replacement_policy, number_of_ways, number_of_sets, set_tags, used_ways):
    if (replacement_policy == "rr"):
        set_round_robin_pointers = [0] * number_of_sets  # RR pointer per set so each set evicts independently.

        def access(block):
            set_index = block & (number_of_sets - 1) # As all set counts are powers of two, bit-mask can be used for better performance.
            tag = block // number_of_sets
            tags = set_tags[set_index]
            ways_used = used_ways[set_index]

            # Search only ways that contain cache lines.
            for way_index in range(ways_used):
                if tags[way_index] == tag:
                    return True

            # Fill unused way before evicting.
            if (number_of_ways > ways_used):
                tags[ways_used] = tag
                used_ways[set_index] = ways_used + 1
                return False

            # Otherwise, set is full so evict with RR and advance rr set pointer.
            victim_way = set_round_robin_pointers[set_index]
            set_round_robin_pointers[set_index] = (victim_way + 1) & (number_of_ways - 1)
            tags[victim_way] = tag
            return False

        return access

    if replacement_policy == "lru":
        # Independent tick counter and LRU state for each set.
        set_lru_ticks = [0] * number_of_sets
        set_lru_state = [[0] * number_of_ways for _ in range(number_of_sets)]

        def access(block):
            set_index = block & (number_of_sets - 1)
            tag = block // number_of_sets
            tags = set_tags[set_index]
            ways_used = used_ways[set_index]
            lru_tick = set_lru_ticks[set_index]
            lru_state = set_lru_state[set_index]

            for way_index in range(ways_used): # Check if line exists in set, if it does then refresh update recency.
                if (tags[way_index] == tag):
                    lru_state[way_index] = lru_tick
                    set_lru_ticks[set_index] = lru_tick + 1
                    return True

            if (number_of_ways > ways_used): # If there are free ways available, fill them before evicting others.
                tags[ways_used] = tag
                used_ways[set_index] = ways_used + 1
                lru_state[ways_used] = lru_tick
                set_lru_ticks[set_index] = lru_tick + 1
                return False

            # Full set pick oldest way by smallest tick (LRU replacement).
            victim_way = 0
            oldest_tick = lru_state[0]
            for way_index in range(1, number_of_ways):
                way_tick = lru_state[way_index]
                if (oldest_tick > way_tick):
                    oldest_tick = way_tick
                    victim_way = way_index

            tags[victim_way] = tag
            lru_state[victim_way] = lru_tick
            set_lru_ticks[set_index] = lru_tick + 1
            return False

        return access

    # LFU set-associative path which uses one min-heap per set.
    set_lfu_state = [[0] * number_of_ways for _ in range(number_of_sets)]
    set_heaps = [[0] * number_of_ways for _ in range(number_of_sets)]
    set_heap_positions = [[-1] * number_of_ways for _ in range(number_of_sets)]
    set_heap_sizes = [0] * number_of_sets

    def access(block):
        set_index = block & (number_of_sets - 1)
        tag = block // number_of_sets
        tags = set_tags[set_index]
        ways_used = used_ways[set_index]
        lfu_state = set_lfu_state[set_index]
        min_heap = set_heaps[set_index]
        heap_positions = set_heap_positions[set_index]
        heap_size = set_heap_sizes[set_index]

        for way_index in range(ways_used):
            if (tags[way_index] == tag):  # Cache hit, so increment frequency and rebalance in set local heap.
                lfu_state[way_index] += 1
                rebalance_lfu_heap_down(min_heap, heap_positions, lfu_state, heap_positions[way_index], heap_size)
                return True

        # If the set is not full, insert into the next free way where ways_used is exactly the first unused way index in the set.
        if (number_of_ways > ways_used):
            tags[ways_used] = tag
            used_ways[set_index] = ways_used + 1 # Move used_ways to next free way for future use.
            lfu_state[ways_used] = 1  #New line has been accessed once on fill, so LFU count starts at 1.
            min_heap[heap_size] = ways_used   # Add this way to the end of the set's LFU heap and record reverse position ie heap index's mapping to way.
            heap_positions[ways_used] = heap_size
            set_heap_sizes[set_index] = heap_size + 1
            rebalance_lfu_heap_up(min_heap, heap_positions, lfu_state, heap_size)    # Rebalance heap order after adding the new way.
            return False

        #Otherwise if not returned by here, set is full and LFU victim is root of the heap.
        victim_way = min_heap[0]
        tags[victim_way] = tag
        lfu_state[victim_way] = 1
        return False

    return access


# Converts cache description from JSON config into runtime cache state.
def build_cache(cache_config):
    line_size = cache_config["line_size"]
    total_cache_lines = cache_config["size"] // line_size
    cache_kind = cache_config["kind"]
    replacement_policy = cache_config.get("replacement_policy", "rr")

    cache_state = {"name": cache_config["name"], "line_size": line_size, "hits": 0, "misses": 0}

    if (cache_kind == "direct"):
        # Using a bytearray for valid bits because it stores only 0/1 bytes and 
        # is faster/'lighter' than a list of bools which would store them as full Python objects.
        # This reduces memory overhead and provides faster access times.
        valid_bits = bytearray(total_cache_lines)
        tags = [0] * total_cache_lines
        cache_state["access"] = direct_accessor(total_cache_lines, valid_bits, tags)
        return cache_state

    if ("way" in cache_kind): # Way in cache kind indicates its value for n in n-way-associative
        number_of_ways = int(cache_kind.split("way", maxsplit=1)[0])
        number_of_sets = total_cache_lines // number_of_ways
        set_tags = [[-1] * number_of_ways for _ in range(number_of_sets)]
        used_ways = [0] * number_of_sets
        cache_state["access"] = set_accessor(replacement_policy, number_of_ways, number_of_sets, set_tags, used_ways)
        return cache_state

    # Support fully-associative kind ("full").
    tags = [0] * total_cache_lines
    tag_to_line = {}
    free_lines = list(range(total_cache_lines - 1, -1, -1))
    cache_state["access"] = full_accessor(replacement_policy, total_cache_lines, tags, tag_to_line, free_lines)
    return cache_state


# Runs the cache simulation using the trace file and contains the program hotloop.
def sim_cache(data, cache_count):
    trace_file = sys.argv[2]

    #Build cache runtime states once, state is saved within the outside 'access' wrappers.
    cache_states = [build_cache(cache_config) for cache_config in data]
    cache_accessors = [cache_state["access"] for cache_state in cache_states]

    # Line sizes are unique to each level, track them so blocks can be translated across levels.
    line_sizes = [cache_state["line_size"] for cache_state in cache_states]
    line_size_pairs = [(line_sizes[level_index], line_sizes[level_index + 1]) for level_index in range(cache_count - 1)]
    first_level_line_size = line_sizes[0]

    # Separate counter arrays to avoid frequent dict writes inside the hotloop
    cache_hits = [0] * cache_count
    cache_misses = [0] * cache_count
    main_memory_accesses = 0
    last_level_index = cache_count - 1

    try:
        with open(trace_file, "rb") as trace_file_handle:
            # Trace file is Memory-mapped for fast sequential reads on large files and to reduce streaming overheads.
            with mmap.mmap(trace_file_handle.fileno(), 0, access=mmap.ACCESS_READ) as trace_map:
                read_line = trace_map.readline
                parse_int = int
                line = read_line()

                while (line): # Trace format is: <pc> <address> <R/W> <size>
                    memory_address = parse_int(line[17:33], 16)
                    memory_size = parse_int(line[36:39])

                    # An access can cross multiple L1 lines, so process each touched block.
                    start_block = memory_address // first_level_line_size
                    end_block = (memory_address + memory_size - 1) // first_level_line_size

                    for level_one_block in range(start_block, end_block + 1):
                        current_block = level_one_block

                        # go from L1 and proceed until hit or main memory is accessed.
                        for level_index in range(cache_count):
                            if (cache_accessors[level_index](current_block)):
                                cache_hits[level_index] += 1
                                break


                            cache_misses[level_index] += 1
                            if (level_index == last_level_index):
                                main_memory_accesses += 1
                                break

                            # Convert block number between levels if line sizes differ.
                            current_level_line_size, next_level_line_size = line_size_pairs[level_index]
                            current_block = (current_block * current_level_line_size) // next_level_line_size

                    line = read_line()

    except FileNotFoundError:
        print(f"Error: The file: {trace_file} was not found.", file=sys.stderr)
        sys.exit(1)

    #Copy hit/miss counters back into cache_state dicts so they can be accurately outputted.
    for level_index in range(cache_count):
        cache_states[level_index]["hits"] = cache_hits[level_index]
        cache_states[level_index]["misses"] = cache_misses[level_index]

    return cache_states, main_memory_accesses
