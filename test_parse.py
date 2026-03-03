import sys
import json
output = sys.stdin.read()
# find the line starting with {"jsonrpc":"2.0","id":2
for line in output.split('\n'):
    if line.startswith('{"jsonrpc":"2.0","id":2'):
        data = json.loads(line)
        print(f"Tools count: {len(data['result']['tools'])}")
        sys.exit(0)
print("Not found")
