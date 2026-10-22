import re

with open('promo_package/interactive_preview.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

patterns = ['realDemoVideo', 'real_screen', r'\.mp4', '<video', 'Video', 'updateDemo']
for pattern in patterns:
    matches = [(i+1, line.strip()[:150]) for i, line in enumerate(lines) if re.search(pattern, line, re.IGNORECASE)]
    if matches:
        print(f'Pattern "{pattern}":')
        for ln, txt in matches[:5]:
            print(f'  L{ln}: {txt}')
    else:
        print(f'Pattern "{pattern}": NOT FOUND')
