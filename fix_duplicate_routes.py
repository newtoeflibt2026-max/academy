path = r'C:\yamen_academy\api_server.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Count occurrences of the duplicate route
count = content.count('@app.route')
count_writing = content.count("/api/writing/evaluate")
count_speaking = content.count("/api/speaking/evaluate")
print(f'Total routes: {count}')
print(f'Writing routes: {count_writing}')
print(f'Speaking routes: {count_speaking}')

# Remove duplicate route blocks — keep only first occurrence of each
# Find the second occurrence and remove the whole block
def remove_duplicate_route(content, route_pattern, func_name):
    parts = content.split(route_pattern)
    if len(parts) > 2:
        # Keep first two parts, remove everything between second and third occurrence
        # Find the next def
        idx = parts[2].find('\n@app.route') 
        if idx > 0:
            parts[2] = parts[2][idx:]
        else:
            # Just remove the duplicate function entirely
            parts = parts[:2]  # keep only first occurrence
        content = route_pattern.join(parts)
    return content

if count_writing > 1:
    content = remove_duplicate_route(content, "/api/writing/evaluate", "evaluate_writing_api")
    print('Removed duplicate writing route')
if count_speaking > 1:
    content = remove_duplicate_route(content, "/api/speaking/evaluate", "evaluate_speaking_api")  
    print('Removed duplicate speaking route')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Done')
