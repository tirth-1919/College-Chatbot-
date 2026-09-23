import httpx, json

c = httpx.Client(timeout=180)
tok = open('audit_token.txt').read().strip()
h = {'Authorization': 'Bearer ' + tok}

tests = [
    'BCA ni fees ketli che?',
    'DBMS kaun padhata hai?',
    'Who teaches DBMS?',
    'show me the AIT library',
    'What is recursion in programming?',
    'Where is her office?',
    'kontu aaloo price kya hai',
]
for q in tests:
    try:
        r = c.post('http://127.0.0.1:8000/api/v1/chat/stream', headers=h,
                   json={'conversation_id': 'audit-lang-1', 'message': q})
        full = ''
        for line in r.text.split('\n'):
            if line.startswith('data: '):
                try:
                    d = json.loads(line[6:])
                    if 'delta' in d:
                        full += d['delta']
                except Exception:
                    pass
        print('Q:', q, '| status', r.status_code)
        print('A:', full[:250].replace('\n', ' '))
        print('---')
    except Exception as e:
        print('Q:', q, 'EXC', type(e).__name__, str(e)[:200])
