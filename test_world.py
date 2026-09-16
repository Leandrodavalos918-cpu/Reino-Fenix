import os, tempfile, importlib.util
from fastapi.testclient import TestClient
fd, path = tempfile.mkstemp(suffix='.db'); os.close(fd); os.unlink(path)
os.environ['FENIX_DB'] = path
spec = importlib.util.spec_from_file_location('server', os.path.join(os.path.dirname(__file__), 'server.py'))
server = importlib.util.module_from_spec(spec); spec.loader.exec_module(server)
with TestClient(server.app) as c:
    s=c.get('/api/stats').json()
    assert (s['population'],s['families'],s['businesses'],s['nobles'])==(2000,179,24,40)
    c.post('/api/advance',json={'days':90}).raise_for_status()
    s=c.get('/api/stats').json(); assert s['chronicles']==90 and s['year']==1 and s['day']==91
    c.post('/api/divine/intervene',json={'action':'wealth','target_type':'person','target_id':1,'parameters':{'amount':1000},'description':'test'}).raise_for_status()
    assert c.get('/api/people/1').json()['wealth']>1000
    c.post('/api/advance',json={'days':275}).raise_for_status()
    s=c.get('/api/stats').json(); assert s['year']==2 and s['day']==1 and s['chronicles']==365
    assert c.get('/api/markets').status_code==200
    assert c.get('/api/crimes').status_code==200
    assert c.get('/api/armies').status_code==200
    assert c.get('/api/divine/history').json()
print('MASTER TEST PASSED')
os.remove(path)
