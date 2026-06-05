import time, urllib.request, json
base='http://127.0.0.1:5000'
for i in range(30):
    try:
        with urllib.request.urlopen(base + '/api/scan/progress', timeout=5) as r:
            data = json.load(r)
            print(i, data['status'], data.get('percent'), data.get('current_task'))
            if data['status'] != 'running':
                print('FINAL', json.dumps(data))
                break
    except Exception as e:
        print('error', e)
    time.sleep(1)
else:
    print('timeout polling')
