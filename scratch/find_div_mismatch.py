def main():
    with open('xapi_sandbox.html', 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    depth = 0
    in_spec = False
    
    print("Tracing div depth inside spec-tab...")
    for idx, line in enumerate(lines):
        line_num = idx + 1
        if 'id="spec-tab"' in line:
            in_spec = True
            print(f"[{line_num}] spec-tab starts! Depth: {depth}")
        if 'id="audit-tab"' in line:
            print(f"[{line_num}] audit-tab starts! Depth: {depth}")
            in_spec = False
            break
            
        if in_spec:
            # Count openings and closings on this line
            import re
            opens = len(re.findall(r'<div\b', line))
            closes = len(re.findall(r'</div>', line))
            if opens > 0 or closes > 0:
                depth += (opens - closes)
                if opens != closes:
                    print(f"  Line {line_num:4}: opens={opens}, closes={closes} | New Depth={depth} | Text: {line.strip()[:60]}")

if __name__ == "__main__":
    main()
