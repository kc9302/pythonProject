def check_tags():
    with open('xapi_sandbox.html', 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Let's track divs
    import re
    
    # We want to find the positions of spec-tab and audit-tab
    spec_pos = content.find('id="spec-tab"')
    audit_pos = content.find('id="audit-tab"')
    main_end_pos = content.find('</main>')
    
    print(f"spec-tab position: {spec_pos}")
    print(f"audit-tab position: {audit_pos}")
    print(f"main end position: {main_end_pos}")
    
    # Let's count divs inside spec-tab (from spec_pos to audit_pos)
    spec_section = content[spec_pos:audit_pos]
    open_divs = len(re.findall(r'<div\b', spec_section))
    close_divs = len(re.findall(r'</div>', spec_section))
    
    print(f"\nInside spec-tab section (between spec-tab and audit-tab):")
    print(f"  * <div: {open_divs}")
    print(f"  * </div>: {close_divs}")
    print(f"  * Net balance (open - close): {open_divs - close_divs}")
    
    # Let's count divs inside audit-tab (from audit_pos to main_end_pos)
    audit_section = content[audit_pos:main_end_pos]
    open_divs_a = len(re.findall(r'<div\b', audit_section))
    close_divs_a = len(re.findall(r'</div>', audit_section))
    
    print(f"\nInside audit-tab section (between audit-tab and </main>):")
    print(f"  * <div: {open_divs_a}")
    print(f"  * </div>: {close_divs_a}")
    print(f"  * Net balance (open - close): {open_divs_a - close_divs_a}")

if __name__ == "__main__":
    check_tags()
