from __future__ import annotations
import json, os, random, sqlite3, threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

BASE=Path(__file__).resolve().parent
DB=Path(os.getenv('FENIX_DB', str(BASE/'reino_fenix.db')))
LOCK=threading.RLock()
app=FastAPI(title='Reino Fénix', version='3.0-master')
R=random.Random(20260916)
KINGDOMS=[(1,'Aurelia','Reina Elira I'),(2,'Valdoria','Rey Darian II')]
CITIES=[(1,1,'Puerto Alba','costa','comercio'),(2,1,'Río Claro','valle','agricultura'),(3,1,'Bosque Alto','bosque','minería'),(4,2,'Corona','llanura','administración'),(5,2,'Monteluz','colinas','ganadería'),(6,2,'Bahía Gris','costa','astilleros')]
RES=['grano','madera','hierro','carbón','piedra','lana','ganado','pescado','sal','vino','herramientas']
ROLES=['agricultor','artesano','mercader','guardia','marinero','minero','constructor','curandero','escriba','pastor','pescador','herrero']
TRAITS=['prudente','ambicioso','leal','curioso','desconfiado','sociable','reservado','arriesgado','paciente','impulsivo']
FIRST=['Aldo','Mara','Nolan','Iria','Tomas','Elian','Vera','Soren','Lia','Bran','Nadia','Oren','Celia','Darin','Mael','Rina','Galen','Talia','Ronan','Ema']
LAST=['Ravel','Veyne','Orlan','Marek','Dorne','Valen','Rios','Alvar','Seren','Kerr','Mont','Arden','Falk','Neris','Vale']
SCHEMA='''
CREATE TABLE IF NOT EXISTS world_state(id INTEGER PRIMARY KEY CHECK(id=1),year INTEGER NOT NULL,day INTEGER NOT NULL,treasury REAL NOT NULL,inflation REAL NOT NULL,paused INTEGER NOT NULL DEFAULT 0,speed INTEGER NOT NULL DEFAULT 1,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS kingdoms(id INTEGER PRIMARY KEY,name TEXT,leader TEXT);
CREATE TABLE IF NOT EXISTS cities(id INTEGER PRIMARY KEY,kingdom_id INTEGER,name TEXT,terrain TEXT,specialty TEXT);
CREATE TABLE IF NOT EXISTS regions(id INTEGER PRIMARY KEY,city_id INTEGER,name TEXT,climate TEXT,soil REAL,security REAL);
CREATE TABLE IF NOT EXISTS people(id INTEGER PRIMARY KEY,name TEXT,sex TEXT,age REAL,health REAL,city_id INTEGER,family_id INTEGER,occupation TEXT,wealth REAL,ambition REAL,loyalty REAL,trait TEXT,alive INTEGER DEFAULT 1,created_year INTEGER,created_day INTEGER);
CREATE TABLE IF NOT EXISTS families(id INTEGER PRIMARY KEY,surname TEXT,home_city INTEGER,wealth REAL,reputation REAL);
CREATE TABLE IF NOT EXISTS relationships(id INTEGER PRIMARY KEY,a INTEGER,b INTEGER,kind TEXT,strength REAL,trust REAL,resentment REAL,UNIQUE(a,b,kind));
CREATE TABLE IF NOT EXISTS memories(id INTEGER PRIMARY KEY,person_id INTEGER,year INTEGER,day INTEGER,text TEXT,importance REAL);
CREATE TABLE IF NOT EXISTS knowledge(id INTEGER PRIMARY KEY,person_id INTEGER,fact TEXT,truth INTEGER,confidence REAL,source_person INTEGER,year INTEGER,day INTEGER,UNIQUE(person_id,fact));
CREATE TABLE IF NOT EXISTS businesses(id INTEGER PRIMARY KEY,city_id INTEGER,owner_id INTEGER,name TEXT,kind TEXT,cash REAL,debt REAL,reputation REAL,operating INTEGER,workers INTEGER,inventory REAL);
CREATE TABLE IF NOT EXISTS markets(id INTEGER PRIMARY KEY,city_id INTEGER,resource TEXT,stock REAL,price REAL,demand REAL,production REAL,consumption REAL,UNIQUE(city_id,resource));
CREATE TABLE IF NOT EXISTS routes(id INTEGER PRIMARY KEY,a_city INTEGER,b_city INTEGER,distance REAL,condition REAL,security REAL,capacity REAL,blocked INTEGER);
CREATE TABLE IF NOT EXISTS shipments(id INTEGER PRIMARY KEY,route_id INTEGER,resource TEXT,quantity REAL,status TEXT,days_left INTEGER,owner_id INTEGER);
CREATE TABLE IF NOT EXISTS nobles(id INTEGER PRIMARY KEY,name TEXT,kingdom_id INTEGER,title TEXT,house_id INTEGER,prestige REAL,wealth REAL,alive INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS houses(id INTEGER PRIMARY KEY,name TEXT,kingdom_id INTEGER,prestige REAL,wealth REAL,estate_count INTEGER);
CREATE TABLE IF NOT EXISTS factions(id INTEGER PRIMARY KEY,kingdom_id INTEGER,name TEXT,influence REAL,stance TEXT);
CREATE TABLE IF NOT EXISTS offices(id INTEGER PRIMARY KEY,kingdom_id INTEGER,name TEXT,holder_id INTEGER);
CREATE TABLE IF NOT EXISTS armies(id INTEGER PRIMARY KEY,kingdom_id INTEGER,name TEXT,commander_id INTEGER,soldiers INTEGER,morale REAL,food REAL,equipment REAL,city_id INTEGER);
CREATE TABLE IF NOT EXISTS conflicts(id INTEGER PRIMARY KEY,name TEXT,kingdom_a INTEGER,kingdom_b INTEGER,status TEXT,intensity REAL,started_year INTEGER,started_day INTEGER);
CREATE TABLE IF NOT EXISTS laws(id INTEGER PRIMARY KEY,kingdom_id INTEGER,name TEXT,effect TEXT,active INTEGER);
CREATE TABLE IF NOT EXISTS crimes(id INTEGER PRIMARY KEY,year INTEGER,day INTEGER,city_id INTEGER,victim_id INTEGER,suspect_id INTEGER,evidence REAL,status TEXT,description TEXT);
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,year INTEGER,day INTEGER,type TEXT,importance REAL,title TEXT,description TEXT,cause TEXT,consequence TEXT);
CREATE TABLE IF NOT EXISTS chronicles(id INTEGER PRIMARY KEY,year INTEGER,day INTEGER,text TEXT);
CREATE TABLE IF NOT EXISTS interventions(id INTEGER PRIMARY KEY,year INTEGER,day INTEGER,action TEXT,target_type TEXT,target_id INTEGER,parameters TEXT,description TEXT,consequence TEXT);
CREATE TABLE IF NOT EXISTS schedules(id INTEGER PRIMARY KEY,execute_year INTEGER,execute_day INTEGER,action TEXT,target_type TEXT,target_id INTEGER,parameters TEXT,description TEXT,done INTEGER DEFAULT 0);
'''

@contextmanager
def db(write=False):
    with LOCK:
        con=sqlite3.connect(DB,timeout=30,isolation_level=None)
        con.row_factory=sqlite3.Row
        con.execute('PRAGMA journal_mode=WAL')
        con.execute('PRAGMA busy_timeout=30000')
        try:
            if write: con.execute('BEGIN IMMEDIATE')
            yield con
            if write: con.commit()
        except Exception:
            if write: con.rollback()
            raise
        finally: con.close()

def q(c,s,p=()): return c.execute(s,p)
def now(): return datetime.now(timezone.utc).isoformat()
def ev(c,y,d,t,imp,title,desc,cause='',cons=''): q(c,'INSERT INTO events(year,day,type,importance,title,description,cause,consequence) VALUES(?,?,?,?,?,?,?,?)',(y,d,t,imp,title,desc,cause,cons))

def seed(c):
    if q(c,'SELECT COUNT(*) n FROM world_state').fetchone()['n']: return
    q(c,'INSERT INTO world_state VALUES(1,1,1,100000,0,0,1,?)',(now(),))
    q(c,'INSERT INTO kingdoms VALUES(?,?,?)',KINGDOMS[0]); q(c,'INSERT INTO kingdoms VALUES(?,?,?)',KINGDOMS[1])
    for x in CITIES: q(c,'INSERT INTO cities VALUES(?,?,?,?,?)',x)
    for cid,k,n,t,s in CITIES: q(c,'INSERT INTO regions VALUES(?,?,?,?,?,?)',(cid,cid,f'Región de {n}',t,0.75 if t=='valle' else 0.58,0.78))
    # 179 households, then 2000 individual people distributed across them.
    for fid in range(1,180):
        city=((fid-1)%6)+1; surname=LAST[(fid-1)%len(LAST)]
        q(c,'INSERT INTO families VALUES(?,?,?,?,?)',(fid,surname,city,R.uniform(800,6000),R.uniform(.4,.8)))
    for pid in range(1,2001):
        fid=((pid-1)%179)+1; city=q(c,'SELECT home_city FROM families WHERE id=?',(fid,)).fetchone()[0]
        age=R.uniform(18,70) if pid<=1600 else R.uniform(0,17)
        sex='M' if pid%2 else 'F'; role=R.choice(ROLES) if age>=14 else 'dependiente'
        wealth=R.uniform(80,1800) if age>=14 else R.uniform(5,300)
        q(c,'INSERT INTO people VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(pid,f'{FIRST[(pid-1)%len(FIRST)]} {LAST[(fid-1)%len(LAST)]}',sex,age,R.uniform(.72,1),city,fid,role,wealth,R.uniform(.2,.9),R.uniform(.3,.95),R.choice(TRAITS),1,1,1))
        if age>=18: q(c,'INSERT OR IGNORE INTO knowledge(person_id,fact,truth,confidence,year,day) VALUES(?,?,?,?,?,?)',(pid,f'La ciudad natal de {pid}',1,R.uniform(.7,1),1,1))
    # family and spouse/kin relationships
    for pid in range(1,2001,2):
        if pid+1<=2000 and q(c,'SELECT age FROM people WHERE id=?',(pid,)).fetchone()[0]>=18 and q(c,'SELECT age FROM people WHERE id=?',(pid+1,)).fetchone()[0]>=18:
            q(c,'INSERT OR IGNORE INTO relationships(a,b,kind,strength,trust,resentment) VALUES(?,?,?,?,?,?)',(pid,pid+1,'pareja',R.uniform(.6,.95),R.uniform(.5,.95),R.uniform(0,.15)))
    for cid,k,n,t,s in CITIES:
        for res in RES: q(c,'INSERT INTO markets(city_id,resource,stock,price,demand,production,consumption) VALUES(?,?,?,?,?,?,?)',(cid,res,R.uniform(80,500),1.0,R.uniform(50,150),0,0))
    for i,(a,b) in enumerate([(1,2),(1,4),(2,3),(2,5),(3,4),(4,6),(5,6)],1): q(c,'INSERT INTO routes VALUES(?,?,?,?,?,?,?,?)',(i,a,b,R.uniform(30,120),R.uniform(.7,.98),R.uniform(.65,.95),R.uniform(40,150),0))
    for cid in range(1,7):
        for j in range(4):
            owner=q(c,'SELECT id FROM people WHERE city_id=? AND alive=1 AND age>=18 ORDER BY id LIMIT 1 OFFSET ?',(cid,j)).fetchone()[0]
            kind=['granja','taller','mercado','servicio'][j]; q(c,'INSERT INTO businesses(city_id,owner_id,name,kind,cash,debt,reputation,operating,workers,inventory) VALUES(?,?,?,?,?,?,?,?,?,?)',(cid,owner,f'{kind.title()} de {cid}-{j+1}',kind,R.uniform(1000,5000),R.uniform(0,1000),R.uniform(.5,.9),1,R.randint(2,8),R.uniform(20,100)))
    for k in range(1,3):
        for j in range(20): q(c,'INSERT INTO houses VALUES(?,?,?,?,?,?)',( (k-1)*20+j+1,f'Casa {"Aurelia" if k==1 else "Valdoria"} {j+1}',k,R.uniform(30,80),R.uniform(5000,25000),R.randint(1,4)))
    for hid in range(1,41):
        h=q(c,'SELECT * FROM houses WHERE id=?',(hid,)).fetchone(); member=q(c,'SELECT id FROM people WHERE city_id=? AND age>=30 ORDER BY RANDOM() LIMIT 1',(((hid-1)%6)+1,)).fetchone()[0]
        q(c,'INSERT INTO nobles VALUES(?,?,?,?,?,?,?,?)',(hid,f'Lord {h[1]}',h[2],'Señor',hid,h[3],h[4],1))
    for kid in (1,2):
        for j,n in enumerate(['Corona','Mercaderes','Reformistas']): q(c,'INSERT INTO factions VALUES(?,?,?,?,?)',((kid-1)*3+j+1,kid,n,R.uniform(20,40),['conservadora','comercial','reformista'][j]))
        for j,n in enumerate(['Consejero Real','Maestre de Hacienda','Comandante','Juez']) : q(c,'INSERT INTO offices VALUES(?,?,?,?)',((kid-1)*4+j+1,kid,n,None))
    for kid in (1,2):
        commander=q(c,'SELECT id FROM nobles WHERE kingdom_id=? LIMIT 1',(kid,)).fetchone()[0]
        q(c,'INSERT INTO armies VALUES(?,?,?,?,?,?,?,?,?)',(kid,kid,f'Ejército de {kid}',commander,1800,0.82,900,0.78,1 if kid==1 else 4))
        q(c,'INSERT INTO laws VALUES(NULL,?,?,?,1)',(kid,'Impuesto ordinario','ingreso fiscal estable'))
    ev(c,1,1,'historia',100,'Comienza la era de Fénix','Las dos coronas entran en una nueva era de observación y cambios autónomos.','fundación','Las instituciones y la población comienzan a actuar bajo sus incentivos.')

def world(c): return dict(q(c,'SELECT * FROM world_state WHERE id=1').fetchone())

def person(c,pid):
    r=q(c,'SELECT * FROM people WHERE id=?',(pid,)).fetchone(); return dict(r) if r else None

def add_memory(c,pid,y,d,text,importance=0.5): q(c,'INSERT INTO memories(person_id,year,day,text,importance) VALUES(?,?,?,?,?)',(pid,y,d,text,importance))

def process_schedules(c,y,d):
    rows=q(c,'SELECT * FROM schedules WHERE done=0 AND (execute_year<? OR (execute_year=? AND execute_day<=?))',(y,y,d)).fetchall()
    for s in rows:
        apply_divine(c,s['action'],s['target_type'],s['target_id'],json.loads(s['parameters'] or '{}'),s['description'],y,d)
        q(c,'UPDATE schedules SET done=1 WHERE id=?',(s['id'],))

def apply_divine(c,action,target_type,target_id,p,y,d,description=''):
    cons=''
    if action=='wealth':
        delta=float(p.get('amount',0)); q(c,'UPDATE people SET wealth=wealth+? WHERE id=?',(delta,target_id)); cons=f'La riqueza de la persona {target_id} cambió en {delta:.0f}.'
    elif action=='health':
        h=max(0,min(1,float(p.get('health',1)))); q(c,'UPDATE people SET health=? WHERE id=?',(h,target_id)); cons=f'La salud de la persona {target_id} fue fijada en {h:.2f}.'
    elif action in ('kill','save'):
        alive=0 if action=='kill' else 1; q(c,'UPDATE people SET alive=?,health=CASE WHEN ?=1 THEN MAX(health,.35) ELSE health END WHERE id=?',(alive,alive,target_id)); cons=f'La vida de la persona {target_id} cambió.'
    elif action=='reveal':
        fact=str(p.get('fact','')); q(c,'INSERT OR REPLACE INTO knowledge(person_id,fact,truth,confidence,source_person,year,day) VALUES(?,?,?,?,?,?,?)',(target_id,fact,1,1,None,y,d)); cons=f'Una verdad llegó al conocimiento de {target_id}.'
    elif action=='erase':
        fact=str(p.get('fact','')); q(c,'DELETE FROM knowledge WHERE person_id=? AND fact=?',(target_id,fact)); cons=f'El conocimiento indicado fue eliminado de {target_id}.'
    elif action=='resource':
        res=p.get('resource','grano'); amount=float(p.get('amount',0)); cid=target_id; q(c,'UPDATE markets SET stock=stock+? WHERE city_id=? AND resource=?',(amount,cid,res)); cons=f'El stock de {res} en la ciudad {cid} cambió en {amount:.0f}.'
    elif action=='weather':
        cons=f'El clima divinamente alterado afecta a la ciudad {target_id} durante los próximos días.'
        q(c,'INSERT INTO knowledge(person_id,fact,truth,confidence,year,day) SELECT id,?,?,?,?,? FROM people WHERE city_id=? AND alive=1 LIMIT 20',(f'Fenómeno climático extraordinario en ciudad {target_id}',1,.9,y,d,target_id))
    else: cons='Intervención registrada sin efecto directo reconocido.'
    q(c,'INSERT INTO interventions VALUES(NULL,?,?,?,?,?,?,?,?)',(y,d,action,target_type,target_id,json.dumps(p,ensure_ascii=False),description,cons)); ev(c,y,d,'divino',95,'Intervención divina',description or action,'acción del Observador',cons)
    return cons

def daily_economy(c,y,d):
    # production -> wages -> consumption -> inventory -> prices -> treasury
    for cid in range(1,7):
        for res in RES:
            m=q(c,'SELECT * FROM markets WHERE city_id=? AND resource=?',(cid,res)).fetchone()
            base={'grano':18,'madera':8,'hierro':5,'carbón':4,'piedra':7,'lana':5,'ganado':3,'pescado':8,'sal':4,'vino':3,'herramientas':2}[res]
            prod=base*R.uniform(.8,1.2); cons=base*R.uniform(.75,1.15)
            weather=1
            if res=='grano': weather=1+R.uniform(-.08,.08)
            prod*=weather
            stock=max(0,m['stock']+prod-cons)
            scarcity=max(.45,min(2.5,(cons+20)/(stock+20)))
            price=max(.2,min(6,m['price']*(0.985+0.03*scarcity)))
            q(c,'UPDATE markets SET stock=?,price=?,demand=?,production=?,consumption=? WHERE id=?',(stock,price,cons,prod,cons,m['id']))
    for b in q(c,'SELECT * FROM businesses WHERE operating=1').fetchall():
        sales=max(0,b['workers']*R.uniform(.8,1.4)); wage=sales*0.42; profit=sales-wage-b['debt']*.001
        cash=b['cash']+profit; debt=max(0,b['debt']-max(0,profit)*.15)
        operating=1 if cash>-500 else 0
        q(c,'UPDATE businesses SET cash=?,debt=?,inventory=MAX(0,inventory+workers*0.2-?*0.1),operating=? WHERE id=?',(cash,debt,sales,operating,b['id']))
        owner=b['owner_id']; q(c,'UPDATE people SET wealth=wealth+? WHERE id=?',(max(0,profit)*.55,owner))
        if not operating: ev(c,y,d,'economia',55,'Negocio en quiebra',f'{b["name"]} dejó de operar por falta de liquidez.','pérdidas y deuda','trabajadores pierden empleo y oferta local disminuye')
    # households consume; workers earn wages from local business pool
    for p in q(c,'SELECT id,age,occupation,wealth FROM people WHERE alive=1 AND age>=14').fetchall():
        wage={'agricultor':2.2,'artesano':3,'mercader':3.5,'guardia':2.8,'marinero':3,'minero':3.2,'constructor':3,'curandero':3.5,'escriba':3,'pastor':2,'pescador':2.6,'herrero':3.4}.get(p['occupation'],1.2)
        q(c,'UPDATE people SET wealth=MAX(0,wealth+?) WHERE id=?',(wage,p['id']))
    revenue=0
    for k in (1,2):
        tax=q(c,'SELECT COALESCE(SUM(wealth)*.0004,0) x FROM people WHERE alive=1 AND city_id IN (SELECT id FROM cities WHERE kingdom_id=?)',(k,)).fetchone()['x']; revenue+=tax
    w=world(c); newtreasury=w['treasury']+revenue
    avg=q(c,'SELECT AVG(price) x FROM markets').fetchone()['x']; inflation=max(-.2,min(2,(avg-1)*.08))
    q(c,'UPDATE world_state SET treasury=?,inflation=?,updated_at=? WHERE id=1',(newtreasury,inflation,now()))
    return revenue

def daily_social(c,y,d):
    # aging, health, births/deaths, marriages, migration and information propagation
    deaths=[]; births=[]
    for p in q(c,'SELECT * FROM people WHERE alive=1').fetchall():
        age=p['age']+1/365
        health=p['health']
        if age>70: health-=0.002
        if p['wealth']<20: health-=0.0007
        if health<=0 or (age>78 and R.random()<.0008):
            q(c,'UPDATE people SET alive=0,health=0,age=? WHERE id=?',(age,p['id'])); deaths.append(p['id']); add_memory(c,p['id'],y,d,'Murió una persona conocida.',.7); continue
        q(c,'UPDATE people SET age=?,health=? WHERE id=?',(age,max(.05,min(1,health)),p['id']))
    # births: roughly one per 2-4 days at this population scale
    if R.random()<.35:
        mother=q(c,'SELECT * FROM people WHERE alive=1 AND sex="F" AND age BETWEEN 20 AND 40 ORDER BY RANDOM() LIMIT 1').fetchone()
        if mother:
            fid=mother['family_id']; city=mother['city_id']; pid=q(c,'SELECT COALESCE(MAX(id),0)+1 n FROM people').fetchone()['n']; sex=R.choice(['M','F']); surname=q(c,'SELECT surname FROM families WHERE id=?',(fid,)).fetchone()[0]
            q(c,'INSERT INTO people VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(pid,f'{R.choice(FIRST)} {surname}',sex,0,0.98,city,fid,'dependiente',R.uniform(0,50),.3,.6,R.choice(TRAITS),1,y,d)); births.append(pid); ev(c,y,d,'demografia',65,'Nuevo nacimiento',f'Nació una nueva persona en {q(c,"SELECT name FROM cities WHERE id=?",(city,)).fetchone()[0]}.','embarazo y familia','crece una nueva generación')
    # relationships transmit a little information
    rels=q(c,'SELECT * FROM relationships WHERE strength>.35').fetchall()
    for r in rels[:120]:
        fact=q(c,'SELECT fact,truth,confidence FROM knowledge WHERE person_id=? ORDER BY RANDOM() LIMIT 1',(r['a'],)).fetchone()
        if fact and R.random()<.22:
            truth=fact['truth'] if R.random()<.88 else 1-fact['truth']; conf=max(.15,min(1,fact['confidence']*R.uniform(.65,1.05)))
            q(c,'INSERT OR REPLACE INTO knowledge(person_id,fact,truth,confidence,source_person,year,day) VALUES(?,?,?,?,?,?,?)',(r['b'],fact['fact'],truth,conf,r['a'],y,d))
    return deaths,births

def daily_politics_security(c,y,d):
    # factions react to prices and treasury; security/crime and simple justice loop
    inflation=world(c)['inflation']
    for f in q(c,'SELECT * FROM factions').fetchall():
        delta=(.5-inflation)*2+R.uniform(-1,1); q(c,'UPDATE factions SET influence=MAX(1,MIN(99,influence+?)) WHERE id=?',(delta,f['id']))
    if R.random()<.10:
        city=R.randint(1,6); victim=q(c,'SELECT id FROM people WHERE alive=1 AND city_id=? ORDER BY RANDOM() LIMIT 1',(city,)).fetchone()
        suspect=q(c,'SELECT id FROM people WHERE alive=1 AND city_id=? AND id!=? ORDER BY RANDOM() LIMIT 1',(city,victim['id'])).fetchone() if victim else None
        if victim and suspect:
            q(c,'INSERT INTO crimes(year,day,city_id,victim_id,suspect_id,evidence,status,description) VALUES(?,?,?,?,?,?,?,?)',(y,d,city,victim['id'],suspect['id'],R.random(),'investigación','Robo o agresión registrada en la ciudad.')); ev(c,y,d,'justicia',45,'Delito registrado','Las autoridades reciben una denuncia y deben investigar.','conflicto entre particulares','la investigación puede producir arresto, juicio o cierre del caso')
    for crime in q(c,'SELECT * FROM crimes WHERE status="investigación"').fetchall():
        if R.random()<.3:
            status='resuelto' if crime['evidence']>.55 else 'sin pruebas'
            q(c,'UPDATE crimes SET status=? WHERE id=?',(status,crime['id']));
            if status=='resuelto': q(c,'UPDATE people SET wealth=MAX(0,wealth-20) WHERE id=?',(crime['suspect_id'],)); ev(c,y,d,'justicia',50,'Investigación resuelta','Una investigación produjo una conclusión.','evidencia reunida','la reputación y riqueza del implicado cambian')
    # military consumes supplies; no arbitrary wars
    for a in q(c,'SELECT * FROM armies').fetchall():
        food=max(0,a['food']+R.uniform(20,50)-a['soldiers']*.015); morale=max(.2,min(1,a['morale']+(food>100)*.005-(food<30)*.02))
        q(c,'UPDATE armies SET food=?,morale=? WHERE id=?',(food,morale,a['id']))

def chronicle(c,y,d,extra=''):
    w=world(c); pop=q(c,'SELECT COUNT(*) x FROM people WHERE alive=1').fetchone()['x']; dead=q(c,'SELECT COUNT(*) x FROM people WHERE alive=0').fetchone()['x']; businesses=q(c,'SELECT COUNT(*) x FROM businesses WHERE operating=1').fetchone()['x']; crimes=q(c,'SELECT COUNT(*) x FROM crimes WHERE year=? AND day=?',(y,d)).fetchone()['x']; births=q(c,'SELECT COUNT(*) x FROM events WHERE year=? AND day=? AND type="demografia"',(y,d)).fetchone()['x'];
    top=q(c,'SELECT title,description FROM events WHERE year=? AND day=? ORDER BY importance DESC LIMIT 5',(y,d)).fetchall(); details=' '.join([r['description'] for r in top])
    text=(f'En el año {y}, día {d}, la población viva es de {pop}. La economía mantiene {businesses} negocios operativos; el tesoro real asciende a {w["treasury"]:.0f} y la inflación estimada es {w["inflation"]*100:.2f}%. Se registraron {births} nacimientos/eventos demográficos y {crimes} delitos. {details} {extra}').strip()
    q(c,'INSERT INTO chronicles(year,day,text) VALUES(?,?,?)',(y,d,text))

def process_day(c):
    w=world(c); y,d=w['year'],w['day']
    daily_economy(c,y,d); deaths,births=daily_social(c,y,d); daily_politics_security(c,y,d); process_schedules(c,y,d)
    if deaths: ev(c,y,d,'demografia',60,'Fallecimientos',f'{len(deaths)} personas murieron durante la jornada.','edad, salud y circunstancias','familias y economías locales se reordenan')
    chronicle(c,y,d)
    d+=1
    if d>365: y+=1; d=1; ev(c,y,d,'historia',40,'Comienza un nuevo año',f'Comienza el año {y}.','paso del tiempo','la población envejece y las instituciones entran en un nuevo ciclo')
    q(c,'UPDATE world_state SET year=?,day=?,updated_at=? WHERE id=1',(y,d,now()))

def run_days(c,n):
    n=max(1,min(int(n),3650))
    for _ in range(n): process_day(c)
    return world(c)

class Advance(BaseModel): days:int=Field(default=1,ge=1,le=3650)
class Divine(BaseModel): action:str; target_type:str='person'; target_id:int=0; parameters:dict={}; description:str=''
class Schedule(BaseModel): execute_year:int; execute_day:int=Field(ge=1,le=365); action:str; target_type:str='person'; target_id:int=0; parameters:dict={}; description:str=''

@app.on_event('startup')
def startup():
    with db(True) as c: c.executescript(SCHEMA); seed(c)

@app.get('/health')
def health():
    with db() as c: return {'ok':True,'world':world(c),'version':app.version}
@app.get('/api/world')
def api_world():
    with db() as c:return world(c)
@app.get('/api/stats')
def stats():
    with db() as c:
        w=world(c); return {'population':q(c,'SELECT COUNT(*) x FROM people WHERE alive=1').fetchone()['x'],'dead':q(c,'SELECT COUNT(*) x FROM people WHERE alive=0').fetchone()['x'],'families':q(c,'SELECT COUNT(*) x FROM families').fetchone()['x'],'businesses':q(c,'SELECT COUNT(*) x FROM businesses WHERE operating=1').fetchone()['x'],'conflicts':q(c,'SELECT COUNT(*) x FROM conflicts WHERE status="active"').fetchone()['x'],'events':q(c,'SELECT COUNT(*) x FROM events').fetchone()['x'],'chronicles':q(c,'SELECT COUNT(*) x FROM chronicles').fetchone()['x'],'nobles':q(c,'SELECT COUNT(*) x FROM nobles WHERE alive=1').fetchone()['x'],'crimes':q(c,'SELECT COUNT(*) x FROM crimes').fetchone()['x'],'shipments':q(c,'SELECT COUNT(*) x FROM shipments WHERE status!="delivered"').fetchone()['x'],'year':w['year'],'day':w['day'],'treasury':round(w['treasury'],2),'inflation':round(w['inflation']*100,3)}
@app.get('/api/people')
def people(limit:int=100,city_id:Optional[int]=None):
    with db() as c:
        sql='SELECT * FROM people WHERE alive=1'; p=[]
        if city_id: sql+=' AND city_id=?'; p.append(city_id)
        sql+=' ORDER BY id LIMIT ?'; p.append(max(1,min(limit,500))); return [dict(x) for x in q(c,sql,p).fetchall()]
@app.get('/api/people/{pid}')
def person_api(pid:int):
    with db() as c:
        p=person(c,pid)
        if not p: raise HTTPException(404,'Persona no encontrada')
        p['knowledge']=[dict(x) for x in q(c,'SELECT fact,truth,confidence,source_person,year,day FROM knowledge WHERE person_id=?',(pid,)).fetchall()]
        p['memories']=[dict(x) for x in q(c,'SELECT year,day,text,importance FROM memories WHERE person_id=? ORDER BY id DESC LIMIT 30',(pid,)).fetchall()]
        p['relationships']=[dict(x) for x in q(c,'SELECT * FROM relationships WHERE a=? OR b=?',(pid,pid)).fetchall()]; return p
@app.get('/api/cities')
def cities():
    with db() as c:return [dict(x) for x in q(c,'SELECT c.*,k.name kingdom FROM cities c JOIN kingdoms k ON k.id=c.kingdom_id').fetchall()]
@app.get('/api/markets')
def markets(city_id:Optional[int]=None):
    with db() as c:return [dict(x) for x in q(c,'SELECT * FROM markets'+(' WHERE city_id=?' if city_id else ''),((city_id,) if city_id else ())).fetchall()]
@app.get('/api/businesses')
def businesses():
    with db() as c:return [dict(x) for x in q(c,'SELECT b.*,c.name city FROM businesses b JOIN cities c ON c.id=b.city_id').fetchall()]
@app.get('/api/factions')
def factions():
    with db() as c:return [dict(x) for x in q(c,'SELECT f.*,k.name kingdom FROM factions f JOIN kingdoms k ON k.id=f.kingdom_id').fetchall()]
@app.get('/api/nobles')
def nobles():
    with db() as c:return [dict(x) for x in q(c,'SELECT n.*,k.name kingdom FROM nobles n JOIN kingdoms k ON k.id=n.kingdom_id WHERE n.alive=1').fetchall()]
@app.get('/api/roads')
def roads():
    with db() as c:return [dict(x) for x in q(c,'SELECT r.*,a.name city_a,b.name city_b FROM routes r JOIN cities a ON a.id=r.a_city JOIN cities b ON b.id=r.b_city').fetchall()]
@app.get('/api/events')
def events(limit:int=50):
    with db() as c:return [dict(x) for x in q(c,'SELECT * FROM events ORDER BY id DESC LIMIT ?',(max(1,min(limit,500)),)).fetchall()]
@app.get('/api/chronicles')
def chronicles(limit:int=30):
    with db() as c:return [dict(x) for x in q(c,'SELECT * FROM chronicles ORDER BY id DESC LIMIT ?',(max(1,min(limit,200)),)).fetchall()]
@app.get('/api/crimes')
def crimes(limit:int=50):
    with db() as c:return [dict(x) for x in q(c,'SELECT * FROM crimes ORDER BY id DESC LIMIT ?',(max(1,min(limit,500)),)).fetchall()]
@app.get('/api/armies')
def armies():
    with db() as c:return [dict(x) for x in q(c,'SELECT * FROM armies').fetchall()]
@app.get('/api/divine/history')
def divine_history(limit:int=100):
    with db() as c:return [dict(x) for x in q(c,'SELECT * FROM interventions ORDER BY id DESC LIMIT ?',(max(1,min(limit,500)),)).fetchall()]
@app.post('/api/advance')
def advance(a:Advance):
    with db(True) as c:
        if world(c)['paused']: return {'ok':False,'paused':True,'world':world(c)}
        return {'ok':True,'world':run_days(c,a.days)}
@app.post('/api/pause')
def pause():
    with db(True) as c:q(c,'UPDATE world_state SET paused=1 WHERE id=1'); return {'ok':True}
@app.post('/api/resume')
def resume():
    with db(True) as c:q(c,'UPDATE world_state SET paused=0 WHERE id=1'); return {'ok':True}
@app.post('/api/speed')
def speed(v:dict):
    with db(True) as c:q(c,'UPDATE world_state SET speed=? WHERE id=1',(max(1,min(100,int(v.get('speed',1)))),)); return {'ok':True}
@app.post('/api/divine/intervene')
def intervene(dv:Divine):
    with db(True) as c:return {'ok':True,'consequence':apply_divine(c,dv.action,dv.target_type,dv.target_id,dv.parameters,dv.description,world(c)['year'],world(c)['day'])}
@app.post('/api/divine/schedule')
def schedule(s:Schedule):
    with db(True) as c:q(c,'INSERT INTO schedules(execute_year,execute_day,action,target_type,target_id,parameters,description) VALUES(?,?,?,?,?,?,?)',(s.execute_year,s.execute_day,s.action,s.target_type,s.target_id,json.dumps(s.parameters,ensure_ascii=False),s.description)); return {'ok':True}

HTML='''<!doctype html><html lang="es"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Reino Fénix — MASTER</title><style>body{font-family:system-ui;background:#0d1015;color:#eee;margin:0}main{max-width:1100px;margin:auto;padding:18px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:10px}.card{background:#171c24;border:1px solid #29303b;border-radius:12px;padding:14px}.toolbar{display:flex;gap:8px;flex-wrap:wrap;margin:15px 0}button{padding:11px 14px;border-radius:9px;border:1px solid #48515f;background:#202733;color:#fff;font-weight:700}.section{margin-top:25px}.chron{border-left:3px solid #778;margin:12px 0;padding-left:12px;line-height:1.5}.small{opacity:.7;font-size:.9em}</style><main><h1>🐦‍🔥 Reino Fénix — MASTER</h1><div class="small">Mundo autónomo · Observador externo · motor causal</div><div class="toolbar"><button onclick="load()">Actualizar</button><button onclick="advance(1)">Avanzar 1 día</button><button onclick="advance(30)">Avanzar 30 días</button><button onclick="advance(365)">Avanzar 1 año</button></div><div id="stats" class="grid"></div><div class="section"><h2>Crónica profunda</h2><div id="chron"></div></div><div class="section"><h2>Eventos recientes</h2><div id="events" class="grid"></div></div><script>async function j(u,o){let r=await fetch(u,o);if(!r.ok)throw Error(await r.text());return r.json()}async function load(){let[s,c,e]=await Promise.all([j('/api/stats'),j('/api/chronicles?limit=10'),j('/api/events?limit=12')]);document.getElementById('stats').innerHTML=Object.entries(s).map(([k,v])=>`<div class=card><b>${k}</b><div>${v}</div></div>`).join('');document.getElementById('chron').innerHTML=c.map(x=>`<div class=chron><b>Año ${x.year}, día ${x.day}</b><br>${x.text}</div>`).join('');document.getElementById('events').innerHTML=e.map(x=>`<div class=card><b>${x.title}</b><br>${x.description}<div class=small>${x.cause||''} → ${x.consequence||''}</div></div>`).join('')}async function advance(n){await j('/api/advance',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({days:n})});load()}load()</script></main></html>'''
@app.get('/',response_class=HTMLResponse)
def home(): return HTML

if __name__=='__main__':
    import uvicorn
    uvicorn.run(app,host='0.0.0.0',port=int(os.getenv('PORT','8000')))
