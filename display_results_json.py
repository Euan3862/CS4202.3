import json
import sys

'''
For each cache, output their hit and miss count alongside the cache name.
At the end of the output also print the number of main memory accesses
which is the number of cache misses of the highest level cache.
'''
def json_results(cache_states, main_memory_accesses):
    caches_out = []
    for cache_state in cache_states:
        caches_out.append(
            {
                "hits": cache_state["hits"],
                "misses": cache_state["misses"],
                "name": cache_state["name"],
            }
        )

    results = {
        "caches": caches_out,
        "main_memory_accesses": main_memory_accesses
    }

    print(json.dumps(results, indent=2), file=sys.stdout)

