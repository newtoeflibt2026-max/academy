import os, re

# Check all templates for placement-related CSS
templates_dir = 'templates'
for fname in os.listdir(templates_dir):
    if fname.endswith('.html'):
        path = os.path.join(templates_dir, fname)
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        if 'placement' in content.lower() or 'اختبار' in content or 'exam' in content.lower():
            print(f'=== {fname} ({len(content)} bytes) ===')
            # Extract CSS blocks
            css_blocks = re.findall(r'<style[^>]*>([\s\S]*?)</style>', content)
            for i, css in enumerate(css_blocks):
                print(f'  CSS block #{i+1}: {len(css)} chars')
                # Show key styling elements
                for key in ['background', 'font-family', 'color', 'border-radius', 'box-shadow', 'card', 'header', 'body']:
                    lines = re.findall(rf'.*{key}.*', css)
                    for l in lines[:2]:
                        print(f'    {l.strip()[:100]}')
            print()
