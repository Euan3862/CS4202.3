import json
import sys

if len(sys.argv) < 3:
    print("Usage: python app.py <config.json> <trace.txt>")
    sys.exit(1)

file_path = sys.argv[1]
trace_file = sys.argv[2]


try:
    with open(file_path, 'r') as file:
        data = json.load(file)
    # print("File data =", data)

except FileNotFoundError:
    print("Error: The file 'data.json' was not found.")

data = data["caches"]
data_length = len(data)

# for x in data:
    # print(x.get("name"))
    # print(x.get("size"))
    # print(x.get("line_size"))
    # print(x.get("kind"))

    # if (len(x) > 4):
        # print(x.get("replacement_policy"))

line_count = 1
traces = []
try:
    with open(trace_file, 'r') as tfile:
        for line in tfile:
            traces.append(line)

except FileNotFoundError:
    print("Error: The file 'data.json' was not found.")



#Best data structure for a cache is a list of sets 
#where each set is a dict mapping tag -> metadata

#Create cache, fill it, deal with edge cases, keep track of work!
print(data)
cache_size = data[0].get("size")
line_size = data[0].get("line_size")
print(cache_size)

total_cache_lines = cache_size / line_size
print(int(total_cache_lines))

# Cache line of memory address 
# = (Block Address) % (Number of lines in cache)

trace_line = traces[0].split(" ")
memory_address = trace_line[1]
memory_size = trace_line[3]

memory_address = int(memory_address, 16)
print(memory_address, memory_size)

cache_line = memory_address % total_cache_lines
print(int(cache_line))

#Need to deal with the case where mem address spans multiple blocks