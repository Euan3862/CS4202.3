import json
import sys

for arg in sys.argv[1:2]:
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

for x in data:
    print("\n")
    print(x.get("name"))
    print(x.get("size"))
    print(x.get("line_size"))
    print(x.get("kind"))

    if (len(x) > 4):
        print(x.get("replacement_policy"))

