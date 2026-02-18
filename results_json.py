import json
import sys

def json_results(hit_count_1, miss_count_1, data, cache_count,hit_count_2=0, miss_count_2=0, hit_count_3=0, miss_count_3=0):
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


