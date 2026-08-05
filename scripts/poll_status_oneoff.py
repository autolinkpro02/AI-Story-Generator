import sys, urllib.request, time, json

if len(sys.argv) < 2:
    print('Usage: poll_status_oneoff.py <token>')
    sys.exit(2)

token = sys.argv[1]
url = f'http://127.0.0.1:8000/status/{token}'

for i in range(60):
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            body = r.read().decode()
            print('RESPONSE', body)
            data = json.loads(body)
            status = data.get('status')
            if status in ('finished','error'):
                break
    except Exception as e:
        print('ERROR', repr(e))
    time.sleep(2)
