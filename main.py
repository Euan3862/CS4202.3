import sys
from parse_config import parse_config_file
from cache_sim import sim_cache
from results_json import json_results

def main():
    data, cache_count = parse_config_file()

    if cache_count == 1:
        hit1, miss1 = sim_cache(data, cache_count)
        json_results(hit1, miss1, data, cache_count)
    elif cache_count == 2:
        hit1, miss1, hit2, miss2 = sim_cache(data, cache_count)
        json_results(hit1, miss1, data, cache_count, hit2, miss2)
    elif cache_count == 3:
        hit1, miss1, hit2, miss2, hit3, miss3 = sim_cache(data, cache_count)
        json_results(hit1, miss1, data, cache_count, hit2, miss2, hit3, miss3)
    else:
        print("Error: only 1, 2, or 3 caches supported.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
