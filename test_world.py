import os,tempfile,subprocess,sys,time,requests
p=tempfile.NamedTemporaryFile(suffix='.db',delete=False); p.close()
env=os.environ.copy(); env['FENIX_DB']=p.name
proc=subprocess.Popen([sys.executable,'-m','uvicorn','server:app','--host','127.0.0.1','--port','8811'],cwd=os.path.dirname(__file__),env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
try:
 for _ in range(50):
  try:
   if requests.get('http://127.0.0.1:8811/health',timeout=1).ok:break
  except: time.sleep(.1)
 assert requests.get('http://127.0.0.1:8811/api/stats').json()['population']==2000
 assert requests.get('http://127.0.0.1:8811/api/stats').json()['families']==179
 requests.post('http://127.0.0.1:8811/api/advance',json={'days':30}).raise_for_status()
 s=requests.get('http://127.0.0.1:8811/api/stats').json(); assert s['population']>=2000 and s['events']>1
 pid=requests.get('http://127.0.0.1:8811/api/people?limit=1').json()[0]['id']
 requests.post('http://127.0.0.1:8811/api/divine/intervene',json={'action':'wealth','target_type':'person','target_id':pid,'parameters':{'amount':5000}}).raise_for_status()
 requests.post('http://127.0.0.1:8811/api/divine/intervene',json={'action':'relation','target_id':pid,'parameters':{'other_id':pid+1,'strength':90}}).raise_for_status()
 requests.post('http://127.0.0.1:8811/api/divine/schedule',json={'execute_year':1,'execute_day':35,'action':'health','target_id':pid,'parameters':{'value':99}}).raise_for_status()
 print('WORLD TEST PASSED')
finally:
 proc.terminate(); proc.wait(timeout=5)
 os.unlink(p.name)
