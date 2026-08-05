import urllib.request, urllib.parse, sys, json

payload = {
    'idea': 'Test story',
    'story_type': 'mystery',
    'visual_style': 'cinematic',
    'duration': '15',
    'character_description': 'A brave child',
    'title': 'Test Story'
}

data = urllib.parse.urlencode(payload).encode()
req = urllib.request.Request('http://127.0.0.1:8000/generate', data=data, headers={'Content-Type': 'application/x-www-form-urlencoded'})

try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print('STATUS', r.status)
        print(r.read().decode())
except Exception as e:
    print('ERROR', repr(e))
    sys.exit(1)
