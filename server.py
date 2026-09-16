from __future__ import annotations
import json, os, random, sqlite3, threading, time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

BASE=Path(__file__).resolve().parent
DB=Path(os.getenv('FENIX_DB', str(BASE/'reino_fenix.db')))
LOCK=threading.RLock(); ENGINE=threading.RLock()
app=FastAPI(title='Reino Fénix', version='2.1-world-expansion')
KINGDOMS=[(1,'Aurelia','Reina Elira I'),(2,'Valdoria','Rey Darian II')]
CITIES=[(1,1,'Puerto Alba','Puerto y comercio'),(2,1,'Río Claro','Valle agrícola'),(3,1,'Bosque Alto','Bosque y minería'),(4,2,'Corona','Capital administrativa'),(5,2,'Monteluz','Ganadería y metalurgia'),(6,2,'Bahía Gris','Puerto y astilleros')]
RES=['grano','madera','hierro','carbón','piedra','lana','ganado','pescado','sal','vino','herramientas']
ROLES=['agricultor','artesano','mercader','guardia','marinero','minero','constructor','curandero','escriba','pastor','pescador','herrero']
TRAITS=['prudente','ambicioso','leal','curioso','desconfiado','sociable','reservado','arriesgado','paciente','impulsivo']
FIRST=['Aldo','Mara','Nolan','Iria','Tomas','Elian','Vera','Soren','Lia','Bran','Nadia','Oren','Celia','Darin','Mael','Rina','Galen','Talia','Ronan','Ema']
LAST=['Ravel','Veyne','Orlan','Marek','Dorne','Valen','Rios','Alvar','Seren','Kerr','Mont','Arden','Falk','Neris','Vale']
SCHEMA='''
CREATE TABLE IF NOT EXISTS world(id INTEGER PRIMARY KEY CHECK(id=1),year INTEGER NOT NULL,day INTEGER NOT NULL,hour INTEGER NOT NULL,speed REAL NOT NULL DEFAULT 24,paused INTEGER NOT NULL DEFAULT 0,last_real REAL NOT NULL,treasury INTEGER NOT NULL,inflation REAL NOT NULL,created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS kingdoms(id INTEGER PRIMARY KEY,name TEXT UNIQUE,ruler TEXT,treasury INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS cities(id INTEGER PRIMARY KEY,kingdom_id INTEGER,name TEXT UNIQUE,description TEXT,population INTEGER DEFAULT 0,prosperity REAL DEFAULT 50,security REAL DEFAULT 70);
CREATE TABLE IF NOT EXISTS families(id INTEGER PRIMARY KEY,surname TEXT,city_id INTEGER,wealth INTEGER DEFAULT 100,prestige REAL DEFAULT 10);
CREATE TABLE IF NOT EXISTS people(id INTEGER PRIMARY KEY,kingdom_id INTEGER,city_id INTEGER,name TEXT,age INTEGER,sex TEXT,alive INTEGER DEFAULT 1,health REAL,wealth INTEGER,role TEXT,trait TEXT,ambition REAL,loyalty REAL,married_to INTEGER,father_id INTEGER,mother_id INTEGER,household_id INTEGER,status TEXT DEFAULT 'ciudadano');
CREATE TABLE IF NOT EXISTS relationships(a INTEGER,b INTEGER,kind TEXT,strength REAL,trust REAL,resentment REAL,PRIMARY KEY(a,b));
CREATE TABLE IF NOT EXISTS knowledge(person_id INTEGER,fact TEXT,truth INTEGER,source_id INTEGER,known_year INTEGER,known_day INTEGER,confidence REAL,PRIMARY KEY(person_id,fact));
CREATE TABLE IF NOT EXISTS memories(id INTEGER PRIMARY KEY,person_id INTEGER,event_id INTEGER,memory TEXT,importance REAL,year INTEGER,day INTEGER);
CREATE TABLE IF NOT EXISTS businesses(id INTEGER PRIMARY KEY,city_id INTEGER,owner_id INTEGER,name TEXT,kind TEXT,workers INTEGER,cash INTEGER,inventory INTEGER,debt INTEGER,active INTEGER DEFAULT 1,reputation REAL DEFAULT 50);
CREATE TABLE IF NOT EXISTS resources(id INTEGER PRIMARY KEY,city_id INTEGER,resource TEXT,quantity INTEGER,price REAL,demand REAL,capacity INTEGER,UNIQUE(city_id,resource));
CREATE TABLE IF NOT EXISTS routes(id INTEGER PRIMARY KEY,origin INTEGER,dest INTEGER,distance INTEGER,security REAL,condition REAL,blocked INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS shipments(id INTEGER PRIMARY KEY,route_id INTEGER,resource TEXT,quantity INTEGER,days_left INTEGER,owner_id INTEGER,status TEXT DEFAULT 'moving');
CREATE TABLE IF NOT EXISTS factions(id INTEGER PRIMARY KEY,kingdom_id INTEGER,name TEXT,influence REAL,goal TEXT,UNIQUE(kingdom_id,name));
CREATE TABLE IF NOT EXISTS offices(id INTEGER PRIMARY KEY,kingdom_id INTEGER,name TEXT,holder_id INTEGER);
CREATE TABLE IF NOT EXISTS armies(id INTEGER PRIMARY KEY,kingdom_id INTEGER,city_id INTEGER,name TEXT,soldiers INTEGER,morale REAL,supplies REAL,commander_id INTEGER);
CREATE TABLE IF NOT EXISTS conflicts(id INTEGER PRIMARY KEY,name TEXT,kingdom_a INTEGER,kingdom_b INTEGER,city_id INTEGER,intensity REAL,cause TEXT,status TEXT,started_year INTEGER,started_day INTEGER,casualties INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS crimes(id INTEGER PRIMARY KEY,year INTEGER,day INTEGER,city_id INTEGER,actor_id INTEGER,victim_id INTEGER,kind TEXT,evidence REAL,status TEXT);
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,year INTEGER,day INTEGER,hour INTEGER,category TEXT,importance INTEGER,title TEXT,description TEXT,cause TEXT,consequence TEXT);
CREATE TABLE IF NOT EXISTS chronicles(id INTEGER PRIMARY KEY,year INTEGER,day INTEGER UNIQUE,text TEXT,created TEXT);
CREATE TABLE IF NOT EXISTS interventions(id INTEGER PRIMARY KEY,year INTEGER,day INTEGER,action TEXT,target_type TEXT,target_id INTEGER,parameters TEXT,description TEXT,consequence TEXT);
CREATE TABLE IF NOT EXISTS schedules(id INTEGER PRIMARY KEY,execute_year INTEGER,execute_day INTEGER,action TEXT,target_type TEXT,target_id INTEGER,parameters TEXT,description TEXT,active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS letters(id INTEGER PRIMARY KEY,year INTEGER,day INTEGER,recipient_id INTEGER,body TEXT,delivered INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS weather(id INTEGER PRIMARY KEY,city_id INTEGER,year INTEGER,day INTEGER,end_year INTEGER,end_day INTEGER,kind TEXT,intensity REAL,active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS projects(id INTEGER PRIMARY KEY,city_id INTEGER,name TEXT,cost INTEGER,progress REAL,required_days INTEGER,status TEXT DEFAULT 'planned');
CREATE TABLE IF NOT EXISTS laws(id INTEGER PRIMARY KEY,kingdom_id INTEGER,name TEXT,effect TEXT,active INTEGER DEFAULT 1);
CREATE INDEX IF NOT EXISTS ix_people_city ON people(city_id,alive); CREATE INDEX IF NOT EXISTS ix_events_date ON events(year,day,hour); CREATE INDEX IF NOT EXISTS ix_mem_person ON memories(person_id);
CREATE TABLE IF NOT EXISTS regions(id INTEGER PRIMARY KEY,kingdom_id INTEGER,name TEXT UNIQUE,terrain TEXT,climate TEXT,description TEXT,development REAL DEFAULT 50);
CREATE TABLE IF NOT EXISTS settlements(id INTEGER PRIMARY KEY,region_id INTEGER,name TEXT UNIQUE,kind TEXT,population INTEGER DEFAULT 0,fortification REAL DEFAULT 0);
CREATE TABLE IF NOT EXISTS noble_houses(id INTEGER PRIMARY KEY,kingdom_id INTEGER,name TEXT UNIQUE,title TEXT,seat_settlement_id INTEGER,wealth INTEGER,prestige REAL,influence REAL,alignment TEXT,goal TEXT,heir_id INTEGER,active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS estates(id INTEGER PRIMARY KEY,house_id INTEGER,region_id INTEGER,name TEXT,type TEXT,size REAL,productivity REAL,workers INTEGER,value INTEGER);
CREATE TABLE IF NOT EXISTS house_members(house_id INTEGER,person_id INTEGER,role TEXT,succession_rank INTEGER,PRIMARY KEY(house_id,person_id));
CREATE TABLE IF NOT EXISTS roads(id INTEGER PRIMARY KEY,origin_settlement_id INTEGER,dest_settlement_id INTEGER,distance INTEGER,condition REAL,security REAL,capacity INTEGER,blocked INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS titles(id INTEGER PRIMARY KEY,person_id INTEGER,house_id INTEGER,title TEXT,start_year INTEGER,start_day INTEGER,end_year INTEGER,end_day INTEGER,active INTEGER DEFAULT 1);
CREATE INDEX IF NOT EXISTS ix_regions_kingdom ON regions(kingdom_id); CREATE INDEX IF NOT EXISTS ix_houses_kingdom ON noble_houses(kingdom_id); CREATE INDEX IF NOT EXISTS ix_estates_house ON estates(house_id);

'''

def con():
 c=sqlite3.connect(DB,timeout=30,check_same_thread=False); c.row_factory=sqlite3.Row
 c.execute('PRAGMA journal_mode=WAL'); c.execute('PRAGMA busy_timeout=30000'); c.execute('PRAGMA synchronous=NORMAL'); c.execute('PRAGMA foreign_keys=ON'); return c
@contextmanager
def db(write=False):
 with LOCK if write else threading.RLock():
  c=con()
  try:
   if write:c.execute('BEGIN IMMEDIATE')
   yield c
   if write:c.commit()
  except: 
   if write:c.rollback()
   raise
  finally:c.close()
def q(c,s,args=()): return c.execute(s,args)
def ev(c,y,d,h,cat,imp,title,desc,cause='',consequence=''):
 q(c,'INSERT INTO events(year,day,hour,category,importance,title,description,cause,consequence) VALUES(?,?,?,?,?,?,?,?,?)',(y,d,h,cat,imp,title,desc,cause,consequence))

def seed(c):
 if q(c,'SELECT COUNT(*) n FROM people').fetchone()['n']: return
 now=time.time(); q(c,'INSERT INTO world VALUES(1,1,1,6,24,0,?,100000,0,?)',(now,datetime.now(timezone.utc).isoformat()))
 # above placeholders: year day hour speed paused last treasury inflation created
 q(c,'DELETE FROM world WHERE id=1'); q(c,'INSERT INTO world VALUES(1,1,1,6,24,0,?,100000,0,?)',(now,datetime.now(timezone.utc).isoformat()))
 for x in KINGDOMS:q(c,'INSERT INTO kingdoms VALUES(?,?,?,?)',(x[0],x[1],x[2],50000))
 for x in CITIES:q(c,'INSERT INTO cities VALUES(?,?,?,?,?,?,?)',(x[0],x[1],x[2],x[3],0,50,70))
 rng=random.Random(424242)
 for i in range(1,180):q(c,'INSERT INTO families VALUES(?,?,?,?,?)',(i,f'{rng.choice(LAST)}{i}',(i-1)%6+1,rng.randint(150,2000),rng.randint(10,60)))
 pid=1
 for kid in (1,2):
  cityids=[x[0] for x in CITIES if x[1]==kid]
  sexes=['M']*500+['F']*500; rng.shuffle(sexes)
  for i,sx in enumerate(sexes):
   age=rng.randint(18,72) if i<850 else rng.randint(1,17); role='estudiante' if age<18 else rng.choice(ROLES); fam=(pid-1)%179+1
   surname=q(c,'SELECT surname FROM families WHERE id=?',(fam,)).fetchone()['surname']
   q(c,'INSERT INTO people VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(pid,kid,cityids[i%3],f'{rng.choice(FIRST)} {surname}',age,sx,1,rng.randint(55,99),rng.randint(20,1800),role,rng.choice(TRAITS),rng.randint(10,95),rng.randint(20,95),None,None,None,fam,'ciudadano')); pid+=1
 # coherent couples: adult opposite sex in same kingdom/city where possible
 for kid in (1,2):
  rows=q(c,'SELECT id,sex FROM people WHERE kingdom_id=? AND age>=18 ORDER BY city_id,id',(kid,)).fetchall(); males=[r['id'] for r in rows if r['sex']=='M']; females=[r['id'] for r in rows if r['sex']=='F']
  for a,b in zip(males[:180],females[:180]):
   q(c,'UPDATE people SET married_to=? WHERE id=?',(b,a)); q(c,'UPDATE people SET married_to=? WHERE id=?',(a,b)); strength=rng.randint(60,95)
   q(c,'INSERT OR REPLACE INTO relationships VALUES(?,?,?,?,?,?)',(a,b,'pareja',strength,rng.randint(55,95),rng.randint(0,10))); q(c,'INSERT OR REPLACE INTO relationships VALUES(?,?,?,?,?,?)',(b,a,'pareja',strength,rng.randint(55,95),rng.randint(0,10)))
 for cid,_,_,_ in CITIES:
  for r in RES:q(c,'INSERT INTO resources(city_id,resource,quantity,price,demand,capacity) VALUES(?,?,?,?,?,?)',(cid,r,rng.randint(800,5000),round(rng.uniform(4,35),2),round(rng.uniform(.8,1.3),2),8000))
  for b in range(4):
   owner=q(c,'SELECT id FROM people WHERE city_id=? AND alive=1 ORDER BY RANDOM() LIMIT 1',(cid,)).fetchone()['id']; kind=rng.choice(['taller','tienda','granja','astillero']); q(c,'INSERT INTO businesses(city_id,owner_id,name,kind,workers,cash,inventory,debt) VALUES(?,?,?,?,?,?,?,?)',(cid,owner,f'Casa {rng.choice(FIRST)} {b}',kind,rng.randint(2,10),rng.randint(1000,7000),rng.randint(50,400),rng.randint(0,3000)))
 routes=[(1,2,50),(2,3,70),(3,4,130),(4,5,80),(5,6,90),(6,1,160),(2,5,140)]
 for i,(a,b,dist) in enumerate(routes,1):q(c,'INSERT INTO routes VALUES(?,?,?,?,?,?,?)',(i,a,b,dist,rng.randint(55,90),rng.randint(60,95),0))
 factions=['Corona','Reformistas','Tradicionalistas']; goals=['preservar el orden','ampliar derechos','defender tradiciones']
 for kid in (1,2):
  for i,n in enumerate(factions):q(c,'INSERT INTO factions(kingdom_id,name,influence,goal) VALUES(?,?,?,?)',(kid,n,rng.randint(20,50),goals[i]))
  for n in ['Consejero','Tesorero','Mariscal','Juez']: holder=q(c,'SELECT id FROM people WHERE kingdom_id=? AND age>=30 ORDER BY RANDOM() LIMIT 1',(kid,)).fetchone()['id']; q(c,'INSERT INTO offices(kingdom_id,name,holder_id) VALUES(?,?,?)',(kid,n,holder))
  city=1 if kid==1 else 4; cmd=q(c,'SELECT id FROM people WHERE city_id=? AND age>=30 ORDER BY RANDOM() LIMIT 1',(city,)).fetchone()['id']; q(c,'INSERT INTO armies(kingdom_id,city_id,name,soldiers,morale,supplies,commander_id) VALUES(?,?,?,?,?,?,?)',(kid,city,'Guardia Real',700,80,90,cmd)); q(c,'INSERT INTO armies(kingdom_id,city_id,name,soldiers,morale,supplies,commander_id) VALUES(?,?,?,?,?,?,?)',(kid,city,'Ejército de Campaña',1800,75,85,cmd))

 # Deep geographic and noble foundation. Idempotent on existing worlds.
 region_defs=[
  (1,1,'Costa del Alba','costa','templado marítimo','Litoral de Aurelia; pesca, sal, comercio y astilleros.',58),
  (2,1,'Valle del Claro','valle fluvial','templado húmedo','Valle agrícola atravesado por el río Claro.',62),
  (3,1,'Bosques de Altara','bosque y colinas','templado','Bosques y tierras altas con madera, hierro, piedra y carbón.',51),
  (4,2,'Corona Central','llanura y colinas','templado continental','Núcleo político y administrativo de Valdoria.',70),
  (5,2,'Tierras de Monteluz','montaña y pastizal','templado seco','Pastizales y montañas dedicados a ganadería y metalurgia.',56),
  (6,2,'Costa Gris','costa rocosa','marítimo fresco','Costa estratégica de comercio, pesca y construcción naval.',60),
 ]
 for r in region_defs:q(c,'INSERT OR IGNORE INTO regions VALUES(?,?,?,?,?,?,?)',r)
 settlement_defs=[(1,1,'Puerto Alba','ciudad',0,45),(2,2,'Río Claro','ciudad',0,15),(3,3,'Bosque Alto','ciudad',0,20),(4,4,'Corona','capital',0,70),(5,5,'Monteluz','ciudad',0,35),(6,6,'Bahía Gris','ciudad',0,45)]
 for x in settlement_defs:q(c,'INSERT OR IGNORE INTO settlements VALUES(?,?,?,?,?,?)',x)
 for cid,region_id in [(1,1),(2,2),(3,3),(4,4),(5,5),(6,6)]:q(c,'UPDATE settlements SET population=(SELECT COUNT(*) FROM people WHERE city_id=? AND alive=1) WHERE id=?',(cid,cid))
 house_names={1:['Casa Avelar','Casa Brisen','Casa Corven','Casa Dalmont','Casa Elar','Casa Feron','Casa Garen','Casa Halvek','Casa Iver','Casa Jastor','Casa Keryn','Casa Lorian','Casa Merrow','Casa Norven','Casa Ordan','Casa Perrin','Casa Quill','Casa Rhen','Casa Sorell','Casa Tervan'],2:['Casa Arven','Casa Brelor','Casa Caster','Casa Draven','Casa Ermont','Casa Falcor','Casa Grisel','Casa Harrow','Casa Ilven','Casa Jorren','Casa Kaldor','Casa Lestyn','Casa Marden','Casa Norell','Casa Orven','Casa Pryce','Casa Queron','Casa Rask','Casa Selwyn','Casa Torren']}
 align=['Corona','Reformistas','Tradicionalistas','Mercantilistas','Militaristas']; goals=['preservar sus tierras','ampliar influencia política','proteger su linaje','dominar una ruta comercial','aumentar su riqueza']
 hid=1
 for kid in (1,2):
  cityids=[x[0] for x in CITIES if x[1]==kid]
  for idx,name in enumerate(house_names[kid]):
   existing=q(c,'SELECT id FROM noble_houses WHERE name=?',(name,)).fetchone()
   if existing: hid=existing['id']+1; continue
   seat=cityids[idx%3]; wealth=5000+rng.randint(0,15000); prestige=35+rng.randint(0,55); influence=20+rng.randint(0,70); alignment=align[idx%len(align)]; goal=goals[idx%len(goals)]
   q(c,'INSERT INTO noble_houses(id,kingdom_id,name,title,seat_settlement_id,wealth,prestige,influence,alignment,goal) VALUES(?,?,?,?,?,?,?,?,?,?)',(hid,kid,name,'Señor',seat,wealth,prestige,influence,alignment,goal))
   candidates=q(c,'SELECT id FROM people WHERE kingdom_id=? AND age>=25 ORDER BY RANDOM() LIMIT 4',(kid,)).fetchall()
   for rank,person in enumerate(candidates,1):
    q(c,'INSERT OR IGNORE INTO house_members VALUES(?,?,?,?)',(hid,person['id'],'señor' if rank==1 else ('heredero' if rank==2 else 'miembro'),rank))
    q(c,'INSERT OR IGNORE INTO titles(person_id,house_id,title,start_year,start_day) VALUES(?,?,?,?,?)',(person['id'],hid,'Señor de '+name.replace('Casa ',''),1,1))
   heir=candidates[1]['id'] if len(candidates)>1 else (candidates[0]['id'] if candidates else None)
   q(c,'UPDATE noble_houses SET heir_id=? WHERE id=?',(heir,hid))
   reg=idx%3+1 if kid==1 else 4+(idx%3); estate_name='Dominio de '+name.replace('Casa ',''); etype=['granja','bosque','mina','viñedo','ganadería'][idx%5]
   q(c,'INSERT INTO estates(house_id,region_id,name,type,size,productivity,workers,value) VALUES(?,?,?,?,?,?,?,?)',(hid,reg,estate_name,etype,rng.uniform(20,400),rng.uniform(.45,.95),rng.randint(10,80),rng.randint(8000,50000)))
   hid+=1
 # Physical roads between principal settlements, separate from abstract trade routes.
 road_defs=[(1,2,52,82,78,20),(2,3,68,67,72,15),(3,4,132,61,68,12),(4,5,82,76,75,20),(5,6,91,73,80,18),(6,1,161,69,76,15),(2,5,145,64,70,10)]
 for i,(a,b,dist,cond,sec,cap) in enumerate(road_defs,1):q(c,'INSERT OR IGNORE INTO roads VALUES(?,?,?,?,?,?,?,?)',(i,a,b,dist,cond,sec,cap,0))

 for p in q(c,'SELECT id FROM people').fetchall(): q(c,'INSERT INTO knowledge VALUES(?,?,?,?,?,?,?)',(p['id'],'El reino existe y la vida cotidiana continúa.',1,None,1,1,1.0))
 ev(c,1,1,6,'fundación',100,'Comienza la era de Fénix','Aurelia y Valdoria entran en el primer día registrado de esta historia.','estado inicial','el mundo queda listo para evolucionar')

@app.on_event('startup')
def startup():
 DB.parent.mkdir(parents=True,exist_ok=True)
 with LOCK:
  c=con(); c.executescript(SCHEMA); seed(c); c.commit(); c.close()

def world(c):return q(c,'SELECT * FROM world WHERE id=1').fetchone()
def next_date(y,d): return (y+1,1) if d>=360 else (y,d+1)
def process_day(c,y,d):
 rng=random.Random(y*100000+d); actions=[]
 # age only at day 360
 if d==360:q(c,'UPDATE people SET age=age+1 WHERE alive=1')
 # households, work, consumption, relationships
 for p in q(c,'SELECT * FROM people WHERE alive=1').fetchall():
  if p['age']<18: continue
  income=rng.randint(0,18)+(3 if p['role'] in ('mercader','herrero','minero') else 0)
  expense=rng.randint(1,10); nw=max(0,p['wealth']+income-expense)
  health=max(0,min(100,p['health']+rng.uniform(-.25,.18)))
  q(c,'UPDATE people SET wealth=?,health=? WHERE id=?',(nw,health,p['id']))
  if health<5 and rng.random()<.03:q(c,'UPDATE people SET alive=0,status=? WHERE id=?',('fallecido',p['id'])); ev(c,y,d,rng.randrange(24),'muerte',65,f'Muere {p["name"]}',f'{p["name"]} fallece tras un deterioro de salud.','salud','su familia y relaciones quedan afectadas'); actions.append('death')
 # births, max 2% yearly household chance via married couples
 if d%30==0:
  couples=q(c,"SELECT a,b FROM relationships WHERE kind='pareja' AND a<b AND strength>55").fetchall()
  for cp in rng.sample(couples,min(len(couples),8)):
   if rng.random()<.22:
    mom=q(c,'SELECT * FROM people WHERE id=? AND alive=1',(cp['b'],)).fetchone(); dad=q(c,'SELECT * FROM people WHERE id=? AND alive=1',(cp['a'],)).fetchone()
    if mom and dad and mom['sex']=='F' and 18<=mom['age']<=45:
     sex=rng.choice(['M','F']); pid=q(c,'SELECT COALESCE(MAX(id),0)+1 n FROM people').fetchone()['n']; fam=mom['household_id']; name=f'{rng.choice(FIRST)} {q(c,"SELECT surname FROM families WHERE id=?",(fam,)).fetchone()["surname"]}'
     q(c,'INSERT INTO people VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(pid,mom['kingdom_id'],mom['city_id'],name,0,sex,1,98,0,'estudiante',rng.choice(TRAITS),rng.randint(10,60),rng.randint(40,90),None,dad['id'],mom['id'],fam,'ciudadano')); ev(c,y,d,10,'familia',45,'Nace un niño',f'{name} nace en {q(c,"SELECT name FROM cities WHERE id=?",(mom["city_id"],)).fetchone()["name"]}.','formación familiar','la familia incorpora una nueva generación'); actions.append('birth')
 # markets and business flows
 for r in q(c,'SELECT * FROM resources').fetchall():
  local_demand=r['demand']*(1+rng.uniform(-.04,.04)); qty=max(0,r['quantity']+rng.randint(-80,120)); price=max(.5,r['price']*(1+(local_demand-1)*.08+rng.uniform(-.015,.015))); q(c,'UPDATE resources SET quantity=?,demand=?,price=? WHERE id=?',(qty,local_demand,price,r['id']))
 for b in q(c,'SELECT * FROM businesses WHERE active=1').fetchall():
  production=max(1,b['workers']*rng.randint(1,4)); sales=min(b['inventory']+production,rng.randint(10,80)); revenue=sales*rng.randint(3,15); wage=b['workers']*rng.randint(1,4); cash=b['cash']+revenue-wage-rng.randint(0,20); inv=max(0,b['inventory']+production-sales)
  debt=b['debt'];
  if cash<0: debt+=abs(cash); cash=0
  active=1 if debt<max(100,b['workers']*1000) else 0
  q(c,'UPDATE businesses SET cash=?,inventory=?,debt=?,active=? WHERE id=?',(cash,inv,debt,active,b['id']))
  if not active: ev(c,y,d,15,'economia',55,'Una empresa cierra',f'{b["name"]} deja de operar tras acumular deudas.','insolvencia','sus trabajadores deben buscar otro empleo')
 # shipments
 for s in q(c,"SELECT * FROM shipments WHERE status='moving'").fetchall():
  left=s['days_left']-1
  if left<=0:
   rt=q(c,'SELECT * FROM routes WHERE id=?',(s['route_id'],)).fetchone(); q(c,'UPDATE shipments SET days_left=0,status=? WHERE id=?',('delivered',s['id'])); q(c,'UPDATE resources SET quantity=MIN(capacity,quantity+?) WHERE city_id=? AND resource=?',(s['quantity'],rt['dest'],s['resource']))
  else:q(c,'UPDATE shipments SET days_left=? WHERE id=?',(left,s['id']))
 # conflicts
 for f in q(c,"SELECT * FROM conflicts WHERE status='active'").fetchall():
  delta=rng.uniform(-6,6); intensity=max(0,min(100,f['intensity']+delta)); casualties=0
  if intensity>45 and rng.random()<.25: casualties=rng.randint(0,8); q(c,'UPDATE conflicts SET casualties=casualties+?,intensity=? WHERE id=?',(casualties,intensity,f['id'])); ev(c,y,d,20,'guerra',70,f'Combate en {f["name"]}',f'El conflicto deja {casualties} bajas registradas.','hostilidades','aumenta la presión sobre recursos y familias')
  else:q(c,'UPDATE conflicts SET intensity=? WHERE id=?',(intensity,f['id']))
  if intensity<3 and rng.random()<.2:q(c,'UPDATE conflicts SET status=? WHERE id=?',('ended',f['id'])); ev(c,y,d,20,'diplomacia',65,f'Termina {f["name"]}','La intensidad cae y las partes dejan de combatir activamente.','agotamiento','comienza una etapa de negociación')
 # treasury/inflation tied to activity, not pure random
 tax=sum(q(c,'SELECT wealth FROM people WHERE alive=1 AND age>=18').fetchall(),0) if False else q(c,'SELECT COALESCE(SUM(wealth),0) s FROM people WHERE alive=1 AND age>=18').fetchone()['s']
 revenue=int(tax*.0008); spending=q(c,'SELECT COUNT(*) n FROM armies').fetchone()['n']*12; w=world(c); treasury=max(0,w['treasury']+revenue-spending); inflation=max(-.1,min(.5,w['inflation']+(spending-revenue)/max(1,treasury)*.0002)); q(c,'UPDATE world SET treasury=?,inflation=? WHERE id=1',(treasury,inflation))
 # city aggregates
 for city in CITIES:q(c,'UPDATE cities SET population=(SELECT COUNT(*) FROM people WHERE city_id=? AND alive=1),prosperity=MAX(0,MIN(100,prosperity+?)) WHERE id=?',(city[0],rng.uniform(-.15,.2),city[0]))
 return actions

def chronicle(c,y,d):
 rows=q(c,'SELECT * FROM events WHERE year=? AND day=? ORDER BY importance DESC,hour,id',(y,d)).fetchall(); w=world(c); pop=q(c,'SELECT COUNT(*) n FROM people WHERE alive=1').fetchone()['n']; avg=q(c,'SELECT COALESCE(AVG(wealth),0) a FROM people WHERE alive=1').fetchone()['a']; active=q(c,'SELECT COUNT(*) n FROM businesses WHERE active=1').fetchone()['n']; conflicts=q(c,"SELECT COUNT(*) n FROM conflicts WHERE status='active'").fetchone()['n']
 parts=[f'En el día {d} del año {y}, el mundo continúa su evolución. La población viva es de {pop} personas y la riqueza media individual ronda {avg:.0f} monedas. Hay {active} empresas activas y {conflicts} conflictos abiertos.']
 for r in rows[:8]:parts.append(f'[{r["category"]}] {r["title"]}: {r["description"]} Causa: {r["cause"]}. Consecuencia registrada: {r["consequence"]}.')
 if not rows:parts.append('La jornada transcurre sin un acontecimiento extraordinario registrado, mientras las actividades económicas, familiares y sociales continúan.')
 text=' '.join(parts); q(c,'INSERT OR REPLACE INTO chronicles(year,day,text,created) VALUES(?,?,?,?)',(y,d,text,datetime.now(timezone.utc).isoformat())); return text

def run_days(n):
 n=max(0,min(int(n),3650)); out=[]
 with ENGINE,db(True) as c:
  w=world(c)
  for _ in range(n):
   y,d=w['year'],w['day']; process_day(c,y,d); out.append(chronicle(c,y,d)); y,d=next_date(y,d); q(c,'UPDATE world SET year=?,day=?,hour=6,last_real=? WHERE id=1',(y,d,time.time())); w=world(c)
 return out

def catchup():
 with ENGINE,db(True) as c:
  w=world(c)
  if w['paused']:return
  elapsed=(time.time()-w['last_real'])/3600*w['speed']; days=min(30,int(elapsed))
 if days:run_days(days)

class Advance(BaseModel): days:int=Field(ge=1,le=3650)
class Speed(BaseModel): speed:float=Field(ge=0,le=365)
class Divine(BaseModel): action:str; target_type:str='person'; target_id:int=0; parameters:dict[str,object]={}; description:str='Intervención divina'
class Schedule(BaseModel): execute_year:int; execute_day:int; action:str; target_type:str='person'; target_id:int=0; parameters:dict[str,object]={}; description:str='Intervención programada'

@app.get('/health')
def health():return {'ok':True,'world':'Reino Fénix'}
@app.get('/api/world')
def api_world():
 catchup()
 with db() as c:
  w=dict(world(c)); w['population']=q(c,'SELECT COUNT(*) n FROM people WHERE alive=1').fetchone()['n']; return w
@app.get('/api/stats')
def stats():
 with db() as c:
  return {'population':q(c,'SELECT COUNT(*) n FROM people WHERE alive=1').fetchone()['n'],'dead':q(c,'SELECT COUNT(*) n FROM people WHERE alive=0').fetchone()['n'],'families':q(c,'SELECT COUNT(*) n FROM families').fetchone()['n'],'businesses':q(c,'SELECT COUNT(*) n FROM businesses WHERE active=1').fetchone()['n'],'conflicts':q(c,"SELECT COUNT(*) n FROM conflicts WHERE status='active'").fetchone()['n'],'events':q(c,'SELECT COUNT(*) n FROM events').fetchone()['n'],'chronicles':q(c,'SELECT COUNT(*) n FROM chronicles').fetchone()['n'],'regions':q(c,'SELECT COUNT(*) n FROM regions').fetchone()['n'],'noble_houses':q(c,'SELECT COUNT(*) n FROM noble_houses WHERE active=1').fetchone()['n'],'estates':q(c,'SELECT COUNT(*) n FROM estates').fetchone()['n'],'roads':q(c,'SELECT COUNT(*) n FROM roads').fetchone()['n']}
@app.get('/api/people')
def people(limit:int=50):
 with db() as c:return [dict(x) for x in q(c,'SELECT * FROM people ORDER BY id LIMIT ?',(max(1,min(limit,500)),)).fetchall()]

@app.get('/api/regions')
def regions():
 with db() as c:
  return [dict(x) for x in q(c,'SELECT r.*,k.name kingdom FROM regions r JOIN kingdoms k ON k.id=r.kingdom_id ORDER BY r.kingdom_id,r.id').fetchall()]
@app.get('/api/settlements')
def settlements():
 with db() as c:
  return [dict(x) for x in q(c,'SELECT s.*,r.name region,k.name kingdom FROM settlements s JOIN regions r ON r.id=s.region_id JOIN kingdoms k ON k.id=r.kingdom_id ORDER BY s.id').fetchall()]
@app.get('/api/nobles')
def nobles(limit:int=100):
 with db() as c:
  rows=q(c,'SELECT h.*,k.name kingdom FROM noble_houses h JOIN kingdoms k ON k.id=h.kingdom_id WHERE h.active=1 ORDER BY h.kingdom_id,h.id LIMIT ?',(max(1,min(limit,100)),)).fetchall()
  out=[]
  for h in rows:
   x=dict(h); x['members']=[dict(m) for m in q(c,'SELECT p.id,p.name,p.age,p.sex,p.role,hm.role house_role,hm.succession_rank FROM house_members hm JOIN people p ON p.id=hm.person_id WHERE hm.house_id=? ORDER BY hm.succession_rank',(h['id'],)).fetchall()]; x['estates']=[dict(e) for e in q(c,'SELECT * FROM estates WHERE house_id=?',(h['id'],)).fetchall()]; out.append(x)
  return out
@app.get('/api/roads')
def roads():
 with db() as c:
  return [dict(x) for x in q(c,'SELECT ro.*,a.name origin,b.name destination FROM roads ro JOIN settlements a ON a.id=ro.origin_settlement_id JOIN settlements b ON b.id=ro.dest_settlement_id ORDER BY ro.id').fetchall()]

@app.get('/api/cities')
def cities():
 with db() as c:return [dict(x) for x in q(c,'SELECT * FROM cities ORDER BY id').fetchall()]
@app.get('/api/events')
def events(limit:int=100):
 with db() as c:return [dict(x) for x in q(c,'SELECT * FROM events ORDER BY id DESC LIMIT ?',(max(1,min(limit,500)),)).fetchall()]
@app.get('/api/chronicles')
def chronicles(limit:int=30):
 with db() as c:return [dict(x) for x in q(c,'SELECT * FROM chronicles ORDER BY id DESC LIMIT ?',(max(1,min(limit,100)),)).fetchall()]
@app.post('/api/advance')
def advance(a:Advance):
 run_days(a.days); return api_world()
@app.post('/api/pause')
def pause():
 with db(True) as c:q(c,'UPDATE world SET paused=1,last_real=? WHERE id=1',(time.time(),)); return {'paused':True}
@app.post('/api/resume')
def resume():
 with db(True) as c:q(c,'UPDATE world SET paused=0,last_real=? WHERE id=1',(time.time(),)); return {'paused':False}
@app.post('/api/speed')
def speed(s:Speed):
 with db(True) as c:q(c,'UPDATE world SET speed=?,last_real=? WHERE id=1',(s.speed,time.time())); return {'speed':s.speed}

def divine_locked(c,dv,y,d):
 p=dv.parameters; action=dv.action; tid=dv.target_id
 if action in ('wealth','kill','save','health','relation','reveal','erase','letter'):
  person=q(c,'SELECT * FROM people WHERE id=?',(tid,)).fetchone()
  if not person:raise HTTPException(404,'Persona no encontrada')
 if action=='wealth':
  amount=int(p.get('amount',0)); q(c,'UPDATE people SET wealth=MAX(0,wealth+?) WHERE id=?',(amount,tid)); cons=f'La riqueza de {person["name"]} cambia en {amount}.'
 elif action=='kill':q(c,"UPDATE people SET alive=0,status='fallecido' WHERE id=?",(tid,)); cons=f'{person["name"]} muere por intervención divina.'
 elif action=='save':q(c,"UPDATE people SET alive=1,status='ciudadano',health=MAX(health,70) WHERE id=?",(tid,)); cons=f'{person["name"]} vuelve a estar con vida.'
 elif action=='health':
  val=float(p.get('value',80)); q(c,'UPDATE people SET health=MAX(0,MIN(100,?)) WHERE id=?',(val,tid)); cons=f'La salud de {person["name"]} pasa a {val:.0f}.'
 elif action=='relation':
  other=int(p.get('other_id',0)); strength=float(p.get('strength',70)); q(c,'INSERT OR REPLACE INTO relationships(a,b,kind,strength,trust,resentment) VALUES(?,?,?,?,?,?)',(tid,other,'relacion',strength,strength,0)); q(c,'INSERT OR REPLACE INTO relationships(a,b,kind,strength,trust,resentment) VALUES(?,?,?,?,?,?)',(other,tid,'relacion',strength,strength,0)); cons='Una relación cambia entre dos personas.'
 elif action=='reveal':
  fact=str(p.get('fact','')); truth=int(bool(p.get('truth',1))); q(c,'INSERT OR REPLACE INTO knowledge VALUES(?,?,?,?,?,?,?)',(tid,fact,truth,None,y,d,float(p.get('confidence',1)))); cons=f'{person["name"]} recibe conocimiento nuevo.'
 elif action=='erase':
  fact=str(p.get('fact','')); q(c,'DELETE FROM knowledge WHERE person_id=? AND fact=?',(tid,fact)); cons=f'El conocimiento indicado desaparece de la memoria informativa de {person["name"]}.'
 elif action=='letter':q(c,'INSERT INTO letters(year,day,recipient_id,body) VALUES(?,?,?,?)',(y,d,tid,str(p.get('body','')))); cons=f'Una carta llega a {person["name"]}.'
 elif action=='resource':
  city=int(p.get('city_id',tid)); res=str(p.get('resource','grano')); amount=int(p.get('amount',0)); q(c,'UPDATE resources SET quantity=MIN(capacity,quantity+?) WHERE city_id=? AND resource=?',(amount,city,res)); cons=f'La disponibilidad de {res} cambia en {city}.'
 elif action=='conflict':
  name=str(p.get('name','Conflicto divino')); ka=int(p.get('kingdom_a',1)); kb=int(p.get('kingdom_b',2)); city=int(p.get('city_id',1)); q(c,'INSERT INTO conflicts(name,kingdom_a,kingdom_b,city_id,intensity,cause,status,started_year,started_day) VALUES(?,?,?,?,?,?,?,?,?)',(name,ka,kb,city,float(p.get('intensity',50)),dv.description,'active',y,d)); cons=f'Surge el conflicto {name}.'
 elif action=='weather':
  city=int(p.get('city_id',tid)); dur=max(1,int(p.get('duration',3))); ey,ed=y,d+dur
  while ed>360:ey+=1;ed-=360
  q(c,'INSERT INTO weather(city_id,year,day,end_year,end_day,kind,intensity) VALUES(?,?,?,?,?,?,?)',(city,y,d,ey,ed,str(p.get('weather','tormenta')),float(p.get('intensity',50)))); cons='El clima de una ciudad cambia por intervención divina.'
 else:raise HTTPException(400,'Acción divina desconocida')
 q(c,'INSERT INTO interventions VALUES(NULL,?,?,?,?,?,?,?,?)',(y,d,action,dv.target_type,tid,json.dumps(p,ensure_ascii=False),dv.description,cons)); ev(c,y,d,6,'divino',100,dv.description,cons,'intervención divina','el mundo debe responder a esta nueva condición'); return cons
@app.post('/api/divine/intervene')
def intervene(dv:Divine):
 with db(True) as c:w=world(c); return {'ok':True,'consequence':divine_locked(c,dv,w['year'],w['day'])}
@app.post('/api/divine/schedule')
def schedule(s:Schedule):
 with db(True) as c:q(c,'INSERT INTO schedules(execute_year,execute_day,action,target_type,target_id,parameters,description) VALUES(?,?,?,?,?,?,?)',(s.execute_year,s.execute_day,s.action,s.target_type,s.target_id,json.dumps(s.parameters,ensure_ascii=False),s.description)); return {'ok':True}
@app.get('/api/divine/history')
def divine_history(limit:int=100):
 with db() as c:return [dict(x) for x in q(c,'SELECT * FROM interventions ORDER BY id DESC LIMIT ?',(max(1,min(limit,500)),)).fetchall()]
@app.get('/',response_class=HTMLResponse)
def home():
 return '''<!doctype html><html lang="es"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Reino Fénix</title><style>body{font-family:system-ui;background:#111;color:#eee;margin:0}main{max-width:1000px;margin:auto;padding:18px}button,input,select,textarea{padding:10px;margin:4px;border-radius:8px;border:1px solid #555;background:#222;color:#eee}button{cursor:pointer}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px}.card{background:#1b1b1b;padding:14px;border-radius:12px}.chron{line-height:1.55;border-left:3px solid #777;padding-left:12px;margin:12px 0}.tabs button{font-weight:700}</style><main><h1>🐦‍🔥 Reino Fénix</h1><p>Simulación autónoma persistente · Observador/Dios</p><div class="tabs"><button onclick="load()">Actualizar</button><button onclick="advance()">Avanzar 1 día</button><button onclick="advance(30)">Avanzar 30 días</button></div><div id="stats" class="grid"></div><h2>Crónicas</h2><div id="chron"></div><h2>Eventos recientes</h2><div id="events"></div><script>async function j(u,o){let r=await fetch(u,o);return r.json()}async function load(){let [s,c,e,w]=await Promise.all([j('/api/stats'),j('/api/chronicles?limit=8'),j('/api/events?limit=12'),j('/api/world')]);document.getElementById('stats').innerHTML=Object.entries({...s,año:w.year,día:w.day,tesoro:w.treasury,inflación:(w.inflation*100).toFixed(2)+'%'}).map(([k,v])=>`<div class=card><b>${k}</b><div>${v}</div></div>`).join('');document.getElementById('chron').innerHTML=c.map(x=>`<div class=chron><b>Año ${x.year}, día ${x.day}</b><br>${x.text}</div>`).join('');document.getElementById('events').innerHTML=e.map(x=>`<div class=card><b>${x.title}</b><br>${x.description}</div>`).join('')}async function advance(n=1){await j('/api/advance',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({days:n})});load()}load()</script></main></html>'''
