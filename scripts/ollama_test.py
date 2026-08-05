import urllib.request, json, traceback

MODEL = "llama3.2:3b"
url = "http://localhost:11434/api/chat"
payload = {"model": MODEL, "messages":[{"role":"user","content":"hello"}]}
req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={"Content-Type":"application/json"})
try:
    with urllib.request.urlopen(req, timeout=20) as resp:
        print('STATUS', resp.status)
        print(resp.read().decode('utf-8'))
except Exception as e:
    print('ERROR', e)
    try:
        # HTTPError has .read()
        body = e.read().decode('utf-8')
        print('RESPONSE BODY:')
        print(body)
    except Exception:
        traceback.print_exc()
