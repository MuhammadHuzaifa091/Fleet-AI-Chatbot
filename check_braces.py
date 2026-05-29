lines = open('static/script.js','r',encoding='utf-8').readlines()
depth = 0
problems = []
for i, l in enumerate(lines, 1):
    o = l.count('{')
    c = l.count('}')
    depth += o - c
    if depth < 0:
        problems.append(f"LINE {i}: depth={depth}")
if problems:
    print("PROBLEMS:")
    for p in problems:
        print(p)
else:
    print("NO NEGATIVE DEPTH - Script should parse OK!")
    print(f"Final depth: {depth}")
