import concurrent.futures, os, tempfile, requests, subprocess, sys, time

# Smoke/integration test for a local running server.
base = os.environ.get('FENIX_TEST_BASE', 'http://127.0.0.1:8811')
print('health', requests.get(base+'/health', timeout=10).json())
print('stats', requests.get(base+'/api/stats', timeout=10).json())
p = requests.get(base+'/api/people?limit=2', timeout=10).json()
a, b = p[0]['id'], p[1]['id']

def wealth(_):
    r=requests.post(base+'/api/divine/intervene',json={'action':'wealth','target_type':'person','target_id':a,'parameters':{'amount':200}},timeout=20)
    return r.status_code

def advance(_):
    return requests.post(base+'/api/advance',json={'days':1},timeout=30).status_code

with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
    codes=list(ex.map(wealth,range(12)))+list(ex.map(advance,range(6)))
assert all(x==200 for x in codes), codes
for action, data in [
    ('health', {'target_type':'person','target_id':a,'parameters':{'health':99}}),
    ('relation', {'parameters':{'person_a':a,'person_b':b,'kind':'amistad','strength':80}}),
    ('reveal', {'target_type':'person','target_id':a,'parameters':{'fact':'Prueba de conocimiento.'}}),
    ('erase', {'target_type':'person','target_id':a,'parameters':{'fact':'Prueba de conocimiento.'}}),
    ('letter', {'target_type':'person','target_id':a,'parameters':{'sender':'Desconocido','body':'Prueba.'}}),
    ('weather', {'parameters':{'city_id':1,'weather':'lluvia','intensity':50,'duration':2}}),
    ('resource', {'parameters':{'city_id':1,'resource':'grano','quantity':100}}),
    ('conflict', {'parameters':{'name':'Prueba','side_a':'A','side_b':'B','intensity':20,'cause':'Prueba.'}}),
    ('kill', {'target_type':'person','target_id':b,'parameters':{}}),
    ('save', {'target_type':'person','target_id':b,'parameters':{}}),
]:
    r=requests.post(base+'/api/divine/intervene',json={'action':action,**data},timeout=20)
    assert r.status_code==200,(action,r.status_code,r.text)
r=requests.post(base+'/api/divine/schedule',json={'action':'wealth','target_type':'person','target_id':a,'parameters':{'amount':123},'execute_in_days':2},timeout=20)
assert r.status_code==200
assert requests.post(base+'/api/advance',json={'days':3},timeout=30).status_code==200
print('ALL TESTS PASSED')
