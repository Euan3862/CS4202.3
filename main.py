from parse_config import parse_config_file
from cache_sim import sim_cache
from display_results_json import json_results

def main():
    data, cache_count = parse_config_file()
    cache_states, main_memory_accesses = sim_cache(data, cache_count)
    json_results(cache_states, main_memory_accesses)

if __name__ == "__main__":
    main()
