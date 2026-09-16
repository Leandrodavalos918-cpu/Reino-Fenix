from __future__ import annotations

import json
import os
import random
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

BASE = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("FENIX_DB", str(BASE / "reino_fenix.db")))

app = FastAPI(title="Reino Fénix", version="1.0.0")

# Todas las escrituras del motor pasan por este lock. SQLite sigue siendo local,
# pero no permitimos escritores concurrentes dentro del proceso.
DB_LOCK = threading.RLock()
ENGINE_LOCK = threading.RLock()

KINGDOMS = [(1, "Aurelia", "Reina Elira I"), (2, "Valdoria", "Rey Darian II")]
CITIES = [
    (1, 1, "Puerto Alba", "Costa occidental y puerto comercial"),
    (2, 1, "Río Claro", "Valle agrícola junto al gran río"),
    (3, 1, "Bosque Alto", "Zona boscosa y minera"),
    (4, 2, "Corona", "Capital y centro administrativo"),
    (5, 2, "Monteluz", "Meseta ganadera y metalúrgica"),
    (6, 2, "Bahía Gris", "Puerto oriental y astilleros"),
]
RESOURCES = ["grano", "madera", "hierro", "carbón", "piedra", "lana", "ganado", "pescado", "sal", "vino", "herramientas"]
FACTION_NAMES = ["Corona", "Reformistas", "Tradicionalistas"]
FIRST = ["Aldo","Mara","Nolan","Iria","Tomas","Elian","Vera","Soren","Lia","Bran","Nadia","Oren","Celia","Darin","Mael","Rina","Galen","Talia","Ronan","Ema"]
LAST = ["Ravel","Veyne","Orlan","Marek","Dorne","Valen","Rios","Alvar","Seren","Kerr","Mont","Arden","Falk","Neris","Vale"]
ROLES = ["agricultor","artesano","mercader","guardia","marinero","minero","constructor","curandero","escriba","pastor","pescador","herrero"]
TRAITS = ["prudente","ambicioso","leal","curioso","desconfiado","sociable","reservado","arriesgado","paciente","impulsivo"]

SCHEMA = r'''
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS world_state (
 id INTEGER PRIMARY KEY CHECK(id=1), year INTEGER NOT NULL, day INTEGER NOT NULL,
 last_real REAL NOT NULL, speed REAL NOT NULL DEFAULT 24.0, paused INTEGER NOT NULL DEFAULT 0,
 treasury INTEGER NOT NULL DEFAULT 100000, inflation REAL NOT NULL DEFAULT 0.0,
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS kingdoms (id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, ruler TEXT NOT NULL, treasury INTEGER NOT NULL DEFAULT 50000);
CREATE TABLE IF NOT EXISTS cities (id INTEGER PRIMARY KEY, kingdom_id INTEGER NOT NULL, name TEXT UNIQUE NOT NULL, description TEXT, population INTEGER NOT NULL DEFAULT 0, prosperity REAL NOT NULL DEFAULT 50, FOREIGN KEY(kingdom_id) REFERENCES kingdoms(id));
CREATE TABLE IF NOT EXISTS districts (id INTEGER PRIMARY KEY, city_id INTEGER NOT NULL, name TEXT NOT NULL, UNIQUE(city_id,name), FOREIGN KEY(city_id) REFERENCES cities(id));
CREATE TABLE IF NOT EXISTS properties (id INTEGER PRIMARY KEY, city_id INTEGER NOT NULL, district_id INTEGER, owner_id INTEGER, kind TEXT NOT NULL, value INTEGER NOT NULL, occupied INTEGER NOT NULL DEFAULT 1, FOREIGN KEY(city_id) REFERENCES cities(id));
CREATE TABLE IF NOT EXISTS people (
 id INTEGER PRIMARY KEY, kingdom_id INTEGER NOT NULL, city_id INTEGER NOT NULL, name TEXT NOT NULL, age INTEGER NOT NULL,
 sex TEXT NOT NULL, alive INTEGER NOT NULL DEFAULT 1, health REAL NOT NULL DEFAULT 80, wealth INTEGER NOT NULL DEFAULT 100,
 role TEXT NOT NULL, trait TEXT NOT NULL, ambition REAL NOT NULL DEFAULT 50, loyalty REAL NOT NULL DEFAULT 50,
 married_to INTEGER, father_id INTEGER, mother_id INTEGER, household_id INTEGER, status TEXT NOT NULL DEFAULT 'citizen',
 FOREIGN KEY(kingdom_id) REFERENCES kingdoms(id), FOREIGN KEY(city_id) REFERENCES cities(id));
CREATE TABLE IF NOT EXISTS families (id INTEGER PRIMARY KEY, surname TEXT NOT NULL, city_id INTEGER NOT NULL, wealth INTEGER NOT NULL DEFAULT 200, FOREIGN KEY(city_id) REFERENCES cities(id));
CREATE TABLE IF NOT EXISTS relationships (person_a INTEGER NOT NULL, person_b INTEGER NOT NULL, kind TEXT NOT NULL, strength INTEGER NOT NULL, PRIMARY KEY(person_a,person_b), FOREIGN KEY(person_a) REFERENCES people(id), FOREIGN KEY(person_b) REFERENCES people(id));
CREATE TABLE IF NOT EXISTS knowledge (person_id INTEGER NOT NULL, fact TEXT NOT NULL, truth INTEGER NOT NULL DEFAULT 1, source_person_id INTEGER, known_day INTEGER NOT NULL DEFAULT 1, PRIMARY KEY(person_id,fact), FOREIGN KEY(person_id) REFERENCES people(id));
CREATE TABLE IF NOT EXISTS memories (id INTEGER PRIMARY KEY, person_id INTEGER NOT NULL, event_id INTEGER, memory TEXT NOT NULL, importance INTEGER NOT NULL DEFAULT 50, created_day INTEGER NOT NULL, FOREIGN KEY(person_id) REFERENCES people(id));
CREATE TABLE IF NOT EXISTS nobles (id INTEGER PRIMARY KEY, person_id INTEGER NOT NULL UNIQUE, title TEXT NOT NULL, house TEXT NOT NULL, power INTEGER NOT NULL, FOREIGN KEY(person_id) REFERENCES people(id));
CREATE TABLE IF NOT EXISTS factions (id INTEGER PRIMARY KEY, kingdom_id INTEGER NOT NULL, name TEXT NOT NULL, influence INTEGER NOT NULL DEFAULT 33, UNIQUE(kingdom_id,name));
CREATE TABLE IF NOT EXISTS offices (id INTEGER PRIMARY KEY, kingdom_id INTEGER NOT NULL, name TEXT NOT NULL, holder_id INTEGER, FOREIGN KEY(kingdom_id) REFERENCES kingdoms(id), FOREIGN KEY(holder_id) REFERENCES people(id));
CREATE TABLE IF NOT EXISTS resources (id INTEGER PRIMARY KEY, city_id INTEGER NOT NULL, resource TEXT NOT NULL, quantity INTEGER NOT NULL, price REAL NOT NULL, demand REAL NOT NULL DEFAULT 1.0, UNIQUE(city_id,resource));
CREATE TABLE IF NOT EXISTS businesses (id INTEGER PRIMARY KEY, city_id INTEGER NOT NULL, owner_id INTEGER, name TEXT NOT NULL, kind TEXT NOT NULL, workers INTEGER NOT NULL, cash INTEGER NOT NULL, active INTEGER NOT NULL DEFAULT 1, FOREIGN KEY(city_id) REFERENCES cities(id), FOREIGN KEY(owner_id) REFERENCES people(id));
CREATE TABLE IF NOT EXISTS routes (id INTEGER PRIMARY KEY, origin_city INTEGER NOT NULL, dest_city INTEGER NOT NULL, distance INTEGER NOT NULL, security INTEGER NOT NULL DEFAULT 70, condition INTEGER NOT NULL DEFAULT 80, FOREIGN KEY(origin_city) REFERENCES cities(id), FOREIGN KEY(dest_city) REFERENCES cities(id));
CREATE TABLE IF NOT EXISTS shipments (id INTEGER PRIMARY KEY, route_id INTEGER NOT NULL, resource TEXT NOT NULL, quantity INTEGER NOT NULL, days_left INTEGER NOT NULL, owner_id INTEGER, status TEXT NOT NULL DEFAULT 'moving', FOREIGN KEY(route_id) REFERENCES routes(id));
CREATE TABLE IF NOT EXISTS conflicts (id INTEGER PRIMARY KEY, name TEXT NOT NULL, side_a TEXT NOT NULL, side_b TEXT NOT NULL, intensity INTEGER NOT NULL, cause TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active', started_day INTEGER NOT NULL, casualties INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, year INTEGER NOT NULL, day INTEGER NOT NULL, category TEXT NOT NULL, importance INTEGER NOT NULL, title TEXT NOT NULL, description TEXT NOT NULL, cause TEXT, consequence TEXT);
CREATE TABLE IF NOT EXISTS chronicles (id INTEGER PRIMARY KEY, year INTEGER NOT NULL, day INTEGER NOT NULL UNIQUE, text TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS divine_interventions (id INTEGER PRIMARY KEY, year INTEGER NOT NULL, day INTEGER NOT NULL, action TEXT NOT NULL, target_type TEXT NOT NULL, target_id INTEGER NOT NULL, parameters TEXT NOT NULL, description TEXT NOT NULL, consequence TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS divine_schedules (id INTEGER PRIMARY KEY, execute_year INTEGER NOT NULL, execute_day INTEGER NOT NULL, action TEXT NOT NULL, target_type TEXT NOT NULL, target_id INTEGER NOT NULL, parameters TEXT NOT NULL, description TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS divine_letters (id INTEGER PRIMARY KEY, year INTEGER NOT NULL, day INTEGER NOT NULL, recipient_id INTEGER NOT NULL, sender_text TEXT NOT NULL, body TEXT NOT NULL, delivered INTEGER NOT NULL DEFAULT 1, FOREIGN KEY(recipient_id) REFERENCES people(id));
CREATE TABLE IF NOT EXISTS divine_weather (id INTEGER PRIMARY KEY, year INTEGER NOT NULL, day INTEGER NOT NULL, city_id INTEGER, weather TEXT NOT NULL, intensity INTEGER NOT NULL, end_day INTEGER NOT NULL, active INTEGER NOT NULL DEFAULT 1);
CREATE INDEX IF NOT EXISTS idx_people_city ON people(city_id,alive);
CREATE INDEX IF NOT EXISTS idx_events_day ON events(year,day);
CREATE INDEX IF NOT EXISTS idx_memory_person ON memories(person_id);
'''


def connect() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA busy_timeout=30000")
    c.execute("PRAGMA synchronous=NORMAL")
    c.execute("PRAGMA foreign_keys=ON")
    return c

@contextmanager
def db(write=False):
    lock = DB_LOCK if write else threading.RLock()
    with lock:
        c = connect()
        try:
            if write: c.execute("BEGIN IMMEDIATE")
            yield c
            if write: c.commit()
        except Exception:
            if write: c.rollback()
            raise
        finally:
            c.close()

def now_iso(): return datetime.now(timezone.utc).isoformat()

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DB_LOCK:
        c = connect()
        c.executescript(SCHEMA)
        if c.execute("SELECT 1 FROM world_state WHERE id=1").fetchone() is None:
            c.execute("INSERT INTO world_state VALUES(1,1,1,?,?,0,100000,0,?)", (time.time(),24.0,now_iso()))
            for kid,name,ruler in KINGDOMS: c.execute("INSERT INTO kingdoms(id,name,ruler) VALUES(?,?,?)",(kid,name,ruler))
            for cid,kid,name,desc in CITIES: c.execute("INSERT INTO cities(id,kingdom_id,name,description) VALUES(?,?,?,?)", (cid,kid,name,desc))
        c.commit(); c.close()
    seed_world()

def seed_world():
    with db(write=True) as c:
        if c.execute("SELECT COUNT(*) n FROM people").fetchone()["n"] > 0:
            return
        random.seed(424242)
        # 17 districts and exactly 63 properties.
        district_plan = {1:3, 2:3, 3:3, 4:3, 5:3, 6:2}
        prop_plan = {1:11, 2:11, 3:11, 4:10, 5:10, 6:10}
        did=1; pid=1
        for cid,_,_,_ in CITIES:
            remaining=prop_plan[cid]
            for j in range(district_plan[cid]):
                c.execute("INSERT INTO districts(id,city_id,name) VALUES(?,?,?)",(did,cid,f"Distrito {j+1}"))
                take = remaining if j == district_plan[cid]-1 else max(1, remaining//(district_plan[cid]-j))
                remaining -= take
                for k in range(take):
                    kind=["vivienda","taller","granja","comercio","almacen"][k%5]
                    c.execute("INSERT INTO properties(id,city_id,district_id,kind,value) VALUES(?,?,?,?,?)",(pid,cid,did,kind,random.randint(80,900)))
                    pid+=1
                did+=1
        # Exactly 179 families.
        for fid in range(1,180):
            cid=CITIES[(fid-1)%len(CITIES)][0]
            surname=f"{LAST[(fid-1)%len(LAST)]}{fid}"
            c.execute("INSERT INTO families(id,surname,city_id,wealth) VALUES(?,?,?,?)",(fid,surname,cid,random.randint(100,1500)))
        # Exactly 2,000 humans: 1,000 per kingdom, 500 male + 500 female per kingdom.
        people_by_city={cid:[] for cid,_,_,_ in CITIES}
        person_id=1
        for kid in [1,2]:
            city_ids=[x[0] for x in CITIES if x[1]==kid]
            sexes=["M"]*500+["F"]*500
            random.shuffle(sexes)
            for i,sex in enumerate(sexes):
                cid=city_ids[i%3]
                age=random.randint(18,72) if i<850 else random.randint(1,17)
                role="estudiante" if age<18 else random.choice(ROLES)
                fam=((person_id-1)%179)+1
                surname=c.execute("SELECT surname FROM families WHERE id=?",(fam,)).fetchone()["surname"]
                name=f"{random.choice(FIRST)} {surname}"
                c.execute("INSERT INTO people(id,kingdom_id,city_id,name,age,sex,health,wealth,role,trait,ambition,loyalty,household_id,status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (person_id,kid,cid,name,age,sex,random.randint(55,99),random.randint(5,1800),role,random.choice(TRAITS),random.randint(10,95),random.randint(15,95),fam,"ciudadano"))
                people_by_city[cid].append(person_id)
                person_id+=1
        # Pair adults and create family/relationship links where possible.
        adults=[r["id"] for r in c.execute("SELECT id FROM people WHERE age>=18 ORDER BY id")]
        for i in range(0,min(600,len(adults)-1),2):
            a,b=adults[i],adults[i+1]
            c.execute("INSERT OR IGNORE INTO relationships VALUES(?,?,?,?)",(a,b,"pareja",random.randint(50,95)))
            c.execute("INSERT OR IGNORE INTO relationships VALUES(?,?,?,?)",(b,a,"pareja",random.randint(50,95)))
            c.execute("UPDATE people SET married_to=? WHERE id=?",(b,a)); c.execute("UPDATE people SET married_to=? WHERE id=?",(a,b))
        # Individual knowledge and memory exist from birth onward.
        for p in c.execute("SELECT id FROM people").fetchall():
            c.execute("INSERT OR IGNORE INTO knowledge VALUES(?,?,1,NULL,1)",(p["id"],"El reino existe y la vida cotidiana continúa."))
            c.execute("INSERT INTO memories(person_id,event_id,memory,importance,created_day) VALUES(?,?,?,?,?)",(p["id"],None,"Recuerdos tempranos de su vida cotidiana.",20,1))
        # 24 businesses, 36 resource markets, 6 cities.
        for cid,_,_,_ in CITIES:
            for r in RESOURCES:
                c.execute("INSERT INTO resources(city_id,resource,quantity,price,demand) VALUES(?,?,?,?,?)",(cid,r,random.randint(300,3000),round(random.uniform(4,40),2),round(random.uniform(.7,1.4),2)))
            for b in range(4):
                owner=random.choice(people_by_city[cid]); c.execute("INSERT INTO businesses(city_id,owner_id,name,kind,workers,cash) VALUES(?,?,?,?,?,?)",(cid,owner,f"Casa {random.choice(FIRST)} {b}",random.choice(["taller","tienda","granja","astillero"]),random.randint(1,8),random.randint(500,6000)))
        # 7 routes.
        routes=[(1,2),(2,3),(3,4),(4,5),(5,6),(6,1),(2,5)]
        for rid,(a,b) in enumerate(routes,1): c.execute("INSERT INTO routes VALUES(?,?,?,?,?,?)",(rid,a,b,random.randint(30,180),random.randint(55,90),random.randint(60,95)))
        # 6 factions (3 per kingdom) and 8 offices (4 per kingdom).
        fid=1
        for kid in [1,2]:
            for fn in FACTION_NAMES:
                c.execute("INSERT INTO factions(id,kingdom_id,name,influence) VALUES(?,?,?,?)",(fid,kid,fn,random.randint(20,50))); fid+=1
            city=1 if kid==1 else 4
            holder=random.choice(people_by_city[city])
            for on in ["Consejero Real","Tesorería","Comandante","Justicia"]:
                c.execute("INSERT INTO offices(kingdom_id,name,holder_id) VALUES(?,?,?)",(kid,on,holder))
        # Exactly 40 nobles.
        noble_ids=[r["id"] for r in c.execute("SELECT id FROM people WHERE age>=18 ORDER BY id LIMIT 40")]
        for n,pid0 in enumerate(noble_ids,1):
            c.execute("INSERT INTO nobles(person_id,title,house,power) VALUES(?,?,?,?)",(pid0,random.choice(["Duque","Conde","Marqués","Barón"]),f"Casa {LAST[n%len(LAST)]}{n}",random.randint(40,95)))
            c.execute("UPDATE people SET status='noble' WHERE id=?",(pid0,))
        c.execute("UPDATE cities SET population=(SELECT COUNT(*) FROM people WHERE people.city_id=cities.id AND alive=1)")
        add_event(c,1,1,"fundación",80,"Comienza la era de Reino Fénix","Las dos coronas y sus ciudades entran en una etapa de paz vigilada.","fundación","Instituciones, familias y mercados comienzan a operar.")
        make_chronicle(c,1,1)

def add_event(c,year,day,category,importance,title,description,cause=None,consequence=None):
    c.execute("INSERT INTO events(year,day,category,importance,title,description,cause,consequence) VALUES(?,?,?,?,?,?,?,?)",(year,day,category,importance,title,description,cause,consequence))

def advance_date(year,day,days=1):
    total=(year-1)*365+(day-1)+days
    return total//365+1,total%365+1

def get_world(c):
    w=c.execute("SELECT * FROM world_state WHERE id=1").fetchone()
    pop=c.execute("SELECT COUNT(*) n FROM people WHERE alive=1").fetchone()["n"]
    avgw=c.execute("SELECT COALESCE(AVG(wealth),0) x FROM people WHERE alive=1").fetchone()["x"]
    return {"year":w["year"],"day":w["day"],"population":pop,"avg_wealth":round(avgw,1),"treasury":w["treasury"],"inflation":round(w["inflation"],2),"speed":w["speed"],"paused":bool(w["paused"]),"kingdoms":[dict(r) for r in c.execute("SELECT * FROM kingdoms")],"cities":[dict(r) for r in c.execute("SELECT * FROM cities")],"conflicts":[dict(r) for r in c.execute("SELECT * FROM conflicts WHERE status='active' ORDER BY intensity DESC")],"events":[dict(r) for r in c.execute("SELECT * FROM events ORDER BY id DESC LIMIT 15")],"chronicle": c.execute("SELECT text FROM chronicles ORDER BY id DESC LIMIT 1").fetchone()["text"]}

def process_day(c,year,day):
    random.seed(year*1000+day)
    actions={"work":0,"study":0,"trade":0,"conversation":0,"travel":0}
    alive=list(c.execute("SELECT id,city_id,age,wealth,health,role,trait FROM people WHERE alive=1"))
    for p in alive:
        if p["age"]<18: actions["study"]+=1
        else:
            actions["work"]+=1
            delta=random.randint(0,20)
            c.execute("UPDATE people SET wealth=MAX(0,wealth+?), health=MIN(100,MAX(0,health+?)) WHERE id=?",(delta,random.choice([-1,0,0,0,1]),p["id"]))
            if random.random()<0.002:
                c.execute("UPDATE people SET health=health-? WHERE id=?",(random.randint(5,20),p["id"]))
        if random.random()<.15: actions["conversation"]+=1
    # market
    for r in c.execute("SELECT id,city_id,resource,quantity,price,demand FROM resources"):
        change=random.uniform(-.03,.03)+(r["demand"]-1)*.02
        new_price=max(.5,r["price"]*(1+change)); qty=max(0,r["quantity"]+random.randint(-40,50))
        demand=min(2,max(.5,r["demand"]+random.uniform(-.04,.04)))
        c.execute("UPDATE resources SET quantity=?,price=?,demand=? WHERE id=?",(qty,new_price,demand,r["id"]))
    # shipments
    for s in c.execute("SELECT * FROM shipments WHERE status='moving'").fetchall():
        left=s["days_left"]-1
        if left<=0:
            c.execute("UPDATE shipments SET days_left=0,status='delivered' WHERE id=?",(s["id"],));
            route=c.execute("SELECT * FROM routes WHERE id=?",(s["route_id"],)).fetchone(); c.execute("UPDATE resources SET quantity=quantity+? WHERE city_id=? AND resource=?",(s["quantity"],route["dest_city"],s["resource"]))
            add_event(c,year,day,"comercio",30,"Llega un cargamento",f"Un cargamento de {s['quantity']} unidades de {s['resource']} llega a su destino.","ruta comercial","Aumenta temporalmente la oferta local.")
        else: c.execute("UPDATE shipments SET days_left=? WHERE id=?",(left,s["id"]))
    # rare births/deaths
    if day%30==0:
        adult=c.execute("SELECT * FROM people WHERE alive=1 AND age BETWEEN 20 AND 42 ORDER BY RANDOM() LIMIT 1").fetchone()
        if adult and random.random()<.65:
            surname=adult["name"].split()[-1]; name=f"{random.choice(FIRST)} {surname}"
            c.execute("INSERT INTO people(kingdom_id,city_id,name,age,sex,health,wealth,role,trait,ambition,loyalty,household_id,mother_id) VALUES((SELECT kingdom_id FROM people WHERE id=?),(SELECT city_id FROM people WHERE id=?),?,?,?,?,?,?,?,?,?,?,?)",(adult["id"],adult["id"],name,0,random.choice(["M","F"]),95,10,"infante",random.choice(TRAITS),10,70,adult["household_id"],adult["id"]))
            add_event(c,year,day,"familia",45,"Nace un niño",f"Nace {name}; una familia incorpora una nueva generación.","familia","Cambian las responsabilidades del hogar.")
    # conflict evolution
    for cf in c.execute("SELECT * FROM conflicts WHERE status='active'").fetchall():
        roll=random.random()
        if roll<.05:
            casualties=random.randint(0,max(1,cf["intensity"]//10)); c.execute("UPDATE conflicts SET casualties=casualties+?, intensity=MIN(100,intensity+?) WHERE id=?",(casualties,random.randint(1,6),cf["id"]))
            add_event(c,year,day,"conflicto",cf["intensity"],f"Escala el conflicto {cf['name']}",f"La tensión entre {cf['side_a']} y {cf['side_b']} provoca nuevas pérdidas y presión política.",cf["cause"],"Aumenta la inestabilidad local.")
        elif roll<.08:
            c.execute("UPDATE conflicts SET intensity=MAX(0,intensity-8) WHERE id=?",(cf["id"],))
    # weather effects
    c.execute("UPDATE divine_weather SET active=0 WHERE active=1 AND ((year<?) OR (year=? AND end_day<?))",(year,year,day))
    w=c.execute("SELECT * FROM world_state WHERE id=1").fetchone()
    treasury_delta=random.randint(-250,450)
    c.execute("UPDATE world_state SET treasury=MAX(0,treasury+?), inflation=MIN(50,MAX(0,inflation+?)) WHERE id=1",(treasury_delta,random.uniform(-.03,.04)))
    c.execute("UPDATE cities SET population=(SELECT COUNT(*) FROM people WHERE people.city_id=cities.id AND alive=1)")
    return actions

def make_chronicle(c,year,day):
    events=list(c.execute("SELECT * FROM events WHERE year=? AND day=? ORDER BY importance DESC,id",(year,day)))
    pop=c.execute("SELECT COUNT(*) n FROM people WHERE alive=1").fetchone()["n"]
    avgw=c.execute("SELECT COALESCE(AVG(wealth),0) x FROM people WHERE alive=1").fetchone()["x"]
    businesses=c.execute("SELECT COUNT(*) n FROM businesses WHERE active=1").fetchone()["n"]
    conflicts=c.execute("SELECT COUNT(*) n FROM conflicts WHERE status='active'").fetchone()["n"]
    res=list(c.execute("SELECT city_id,resource,price,demand FROM resources ORDER BY demand DESC LIMIT 3"))
    text=f"Día {day} del año {year}. Han transcurrido 24 horas dentro de Reino Fénix. La población viva es de {pop:,} personas y la riqueza media individual ronda {avgw:.0f} monedas. Hay {businesses} negocios activos y {conflicts} conflictos abiertos.\n\n"
    if events:
        text += "Durante la jornada: " + " ".join(e["description"] for e in events[:5]) + "\n\n"
    else: text += "No se registró un acontecimiento extraordinario de alta importancia; la vida cotidiana continuó entre trabajo, estudio, comercio, relaciones y decisiones privadas.\n\n"
    if res: text += "Mercados bajo presión: " + ", ".join(f"{r['resource']} (demanda {r['demand']:.2f}, precio {r['price']:.1f})" for r in res) + ".\n\n"
    text += "La crónica describe hechos registrados por el motor. La información divina permanece separada del conocimiento de los habitantes."
    c.execute("INSERT OR REPLACE INTO chronicles(year,day,text,created_at) VALUES(?,?,?,?)",(year,day,text,now_iso()))
    return text

def process_schedules(c):
    w=c.execute("SELECT year,day FROM world_state WHERE id=1").fetchone(); due=c.execute("SELECT * FROM divine_schedules WHERE active=1 AND (execute_year<? OR (execute_year=? AND execute_day<=?))",(w["year"],w["year"],w["day"])).fetchall()
    for s in due:
        execute_divine_locked(c,s["action"],s["target_type"],s["target_id"],json.loads(s["parameters"]),s["description"],record_day=(w["year"],w["day"]))
        c.execute("UPDATE divine_schedules SET active=0 WHERE id=?",(s["id"],))

def execute_divine_locked(c,action,target_type,target_id,params,description="",record_day=None):
    w=c.execute("SELECT year,day FROM world_state WHERE id=1").fetchone(); y,d=record_day or (w["year"],w["day"]); consequence=""
    if target_type=="person":
        p=c.execute("SELECT * FROM people WHERE id=?",(target_id,)).fetchone()
        if not p: raise HTTPException(404,"Persona no encontrada")
    if action=="wealth":
        amount=int(params.get("amount",0));
        if amount<0: raise HTTPException(400,"La riqueza debe ser positiva")
        c.execute("UPDATE people SET wealth=wealth+? WHERE id=?",(amount,target_id)); consequence=f"{p['name']} recibió {amount} monedas. Su patrimonio pasó de {p['wealth']} a {p['wealth']+amount}."
    elif action=="kill":
        c.execute("UPDATE people SET alive=0,status='muerto' WHERE id=?",(target_id,)); consequence=f"{p['name']} murió por una intervención divina. El resto del mundo no conoce la causa sobrenatural."
        add_event(c,y,d,"muerte",80,"Una vida termina",consequence,"intervención divina","La familia, propiedades y relaciones quedan expuestas a consecuencias posteriores.")
    elif action=="save":
        c.execute("UPDATE people SET alive=1,health=MAX(health,70),status='ciudadano' WHERE id=?",(target_id,)); consequence=f"{p['name']} fue salvado y recuperó su condición vital."
    elif action=="health":
        amount=max(0,min(100,int(params.get("health",100)))); c.execute("UPDATE people SET health=? WHERE id=?",(amount,target_id)); consequence=f"La salud de {p['name']} quedó en {amount}/100."
    elif action=="relation":
        a=int(params.get("person_a",target_id)); b=int(params.get("person_b",0)); strength=max(-100,min(100,int(params.get("strength",0)))); kind=params.get("kind","relación");
        if not b or not c.execute("SELECT 1 FROM people WHERE id=?",(b,)).fetchone(): raise HTTPException(400,"La segunda persona no existe")
        c.execute("INSERT INTO relationships VALUES(?,?,?,?) ON CONFLICT(person_a,person_b) DO UPDATE SET kind=excluded.kind,strength=excluded.strength",(a,b,kind,strength)); consequence=f"La relación entre dos habitantes fue alterada a {strength}/100 ({kind})."
    elif action=="reveal":
        fact=str(params.get("fact","")).strip();
        if not fact: raise HTTPException(400,"Falta la información a revelar")
        c.execute("INSERT INTO knowledge(person_id,fact,truth,source_person_id,known_day) VALUES(?,?,1,NULL,?) ON CONFLICT(person_id,fact) DO UPDATE SET truth=1,known_day=excluded.known_day",(target_id,fact,d)); consequence=f"{p['name']} ahora conoce: {fact}"
    elif action=="erase":
        fact=str(params.get("fact","")).strip(); c.execute("DELETE FROM knowledge WHERE person_id=? AND fact=?",(target_id,fact)); consequence=f"Se eliminó de la memoria de conocimiento de {p['name']} el hecho indicado."
    elif action=="letter":
        body=str(params.get("body","")).strip(); sender=str(params.get("sender","Una voz desconocida")).strip(); c.execute("INSERT INTO divine_letters(year,day,recipient_id,sender_text,body) VALUES(?,?,?,?,?)",(y,d,target_id,sender,body)); consequence=f"Una carta fue entregada a {p['name']} con remitente aparente '{sender}'."
    elif action=="weather":
        weather=str(params.get("weather","lluvia")); intensity=max(1,min(100,int(params.get("intensity",50)))); duration=max(1,int(params.get("duration",1))); city_id=int(params.get("city_id",0)) or None; end_day=d+duration; c.execute("INSERT INTO divine_weather(year,day,city_id,weather,intensity,end_day) VALUES(?,?,?,?,?,?)",(y,d,city_id,weather,intensity,end_day)); consequence=f"El clima cambió a {weather} con intensidad {intensity} durante {duration} día(s)."
    elif action=="resource":
        resource=str(params.get("resource","grano")); qty=max(1,int(params.get("quantity",1))); city_id=int(params.get("city_id",1)); c.execute("UPDATE resources SET quantity=quantity+? WHERE city_id=? AND resource=?",(qty,city_id,resource)); consequence=f"Aparecieron {qty} unidades adicionales de {resource}."
    elif action=="conflict":
        name=str(params.get("name","Conflicto divino")); a=str(params.get("side_a","Facción A")); b=str(params.get("side_b","Facción B")); intensity=max(1,min(100,int(params.get("intensity",50)))); cause=str(params.get("cause","Una causa desconocida para los habitantes.")); c.execute("INSERT INTO conflicts(name,side_a,side_b,intensity,cause,started_day) VALUES(?,?,?,?,?,?)",(name,a,b,intensity,cause,d)); consequence=f"Comenzó el conflicto '{name}' entre {a} y {b}."
    else: raise HTTPException(400,"Acción divina no reconocida")
    c.execute("INSERT INTO divine_interventions(year,day,action,target_type,target_id,parameters,description,consequence) VALUES(?,?,?,?,?,?,?,?)",(y,d,action,target_type,target_id,json.dumps(params,ensure_ascii=False),description or action,consequence))
    return consequence

def simulate(days:int):
    days=max(0,int(days));
    with ENGINE_LOCK, db(write=True) as c:
        w=c.execute("SELECT * FROM world_state WHERE id=1").fetchone()
        y,d=w["year"],w["day"]
        if w["paused"]: return get_world(c)
        for _ in range(days):
            y,d=advance_date(y,d,1); process_day(c,y,d); process_schedules(c); make_chronicle(c,y,d)
        c.execute("UPDATE world_state SET year=?,day=?,last_real=? WHERE id=1",(y,d,time.time()))
        return get_world(c)

def catch_up():
    with ENGINE_LOCK:
        with db(write=True) as c:
            w=c.execute("SELECT * FROM world_state WHERE id=1").fetchone()
            if w["paused"]: return
            elapsed=max(0,time.time()-w["last_real"])
            # speed = simulated days per real hour. Default 24 => 1 sim day/hour.
            days=int(elapsed/3600*w["speed"])
            if days>0:
                y,d=w["year"],w["day"]
                for _ in range(min(days,3650)):
                    y,d=advance_date(y,d,1); process_day(c,y,d); process_schedules(c); make_chronicle(c,y,d)
                c.execute("UPDATE world_state SET year=?,day=?,last_real=? WHERE id=1",(y,d,time.time()))
            else:
                c.execute("UPDATE world_state SET last_real=? WHERE id=1",(time.time(),))

@app.on_event("startup")
def startup(): init_db()

class DivineAction(BaseModel):
    action:str
    target_type:str="world"
    target_id:int=0
    parameters:dict[str,Any]=Field(default_factory=dict)
    description:str=""
class AdvanceRequest(BaseModel): days:int=Field(default=1,ge=1,le=3650)
class ScheduleRequest(DivineAction): execute_in_days:int=Field(default=1,ge=1,le=3650)

@app.get("/health")
def health():
    with db() as c:
        w=c.execute("SELECT year,day FROM world_state WHERE id=1").fetchone()
        return {"ok":True,"service":"reino-fenix","year":w["year"],"day":w["day"]}

@app.get("/",response_class=HTMLResponse)
def home(): return HTML

@app.get("/api/world")
def api_world():
    catch_up()
    with db() as c: return get_world(c)

@app.get("/api/people")
def people(q:str="",city_id:int=0,limit:int=100):
    catch_up()
    with db() as c:
        rows=c.execute("SELECT id,name,age,sex,city_id,kingdom_id,health,wealth,role,trait,ambition,loyalty,alive,status FROM people WHERE (?='' OR name LIKE ?) AND (?=0 OR city_id=?) ORDER BY alive DESC,name LIMIT ?",(q,f"%{q}%",city_id,city_id,min(limit,500))).fetchall()
        return [dict(r) for r in rows]

@app.get("/api/people/{pid}")
def person(pid:int):
    catch_up()
    with db() as c:
        p=c.execute("SELECT p.*,c.name city_name,k.name kingdom_name FROM people p JOIN cities c ON c.id=p.city_id JOIN kingdoms k ON k.id=p.kingdom_id WHERE p.id=?",(pid,)).fetchone()
        if not p: raise HTTPException(404,"Persona no encontrada")
        d=dict(p); d["relationships"]=[dict(r) for r in c.execute("SELECT r.*,p.name other_name FROM relationships r JOIN people p ON p.id=r.person_b WHERE r.person_a=?",(pid,))]; d["knowledge"]=[dict(r) for r in c.execute("SELECT fact,truth,known_day FROM knowledge WHERE person_id=?",(pid,))]; return d

@app.get("/api/cities")
def cities():
    catch_up()
    with db() as c: return [dict(r) for r in c.execute("SELECT c.*,k.name kingdom_name FROM cities c JOIN kingdoms k ON k.id=c.kingdom_id ORDER BY c.id")]

@app.get("/api/layers")
def layers():
    catch_up()
    with db() as c:
        return {"cities":[dict(r) for r in c.execute("SELECT * FROM cities")],"resources":[dict(r) for r in c.execute("SELECT * FROM resources")],"routes":[dict(r) for r in c.execute("SELECT * FROM routes")],"factions":[dict(r) for r in c.execute("SELECT * FROM factions")],"offices":[dict(r) for r in c.execute("SELECT * FROM offices")],"nobles":[dict(r) for r in c.execute("SELECT * FROM nobles")],"businesses":[dict(r) for r in c.execute("SELECT * FROM businesses")],"conflicts":[dict(r) for r in c.execute("SELECT * FROM conflicts")],"families":c.execute("SELECT COUNT(*) n FROM families").fetchone()["n"],"properties":c.execute("SELECT COUNT(*) n FROM properties").fetchone()["n"]}

@app.post("/api/advance")
def advance(req:AdvanceRequest): return simulate(req.days)

@app.post("/api/pause")
def pause():
    with ENGINE_LOCK, db(write=True) as c: c.execute("UPDATE world_state SET paused=1,last_real=? WHERE id=1",(time.time(),)); return get_world(c)
@app.post("/api/resume")
def resume():
    with ENGINE_LOCK, db(write=True) as c: c.execute("UPDATE world_state SET paused=0,last_real=? WHERE id=1",(time.time(),)); return get_world(c)
@app.post("/api/speed")
def speed(value:float):
    if value<0 or value>365: raise HTTPException(400,"Velocidad fuera de rango")
    with ENGINE_LOCK, db(write=True) as c: c.execute("UPDATE world_state SET speed=?,last_real=? WHERE id=1",(value,time.time(),)); return get_world(c)

@app.post("/api/divine/intervene")
def intervene(req:DivineAction):
    with ENGINE_LOCK, db(write=True) as c:
        consequence=execute_divine_locked(c,req.action,req.target_type,req.target_id,req.parameters,req.description)
        return {"ok":True,"consequence":consequence,"world":get_world(c)}

@app.post("/api/divine/schedule")
def schedule(req:ScheduleRequest):
    with ENGINE_LOCK, db(write=True) as c:
        w=c.execute("SELECT year,day FROM world_state WHERE id=1").fetchone(); y,d=advance_date(w["year"],w["day"],req.execute_in_days); c.execute("INSERT INTO divine_schedules(execute_year,execute_day,action,target_type,target_id,parameters,description) VALUES(?,?,?,?,?,?,?)",(y,d,req.action,req.target_type,req.target_id,json.dumps(req.parameters,ensure_ascii=False),req.description)); return {"ok":True,"execute_year":y,"execute_day":d}

@app.get("/api/divine/history")
def divine_history():
    with db() as c: return {"interventions":[dict(r) for r in c.execute("SELECT * FROM divine_interventions ORDER BY id DESC LIMIT 50")],"schedules":[dict(r) for r in c.execute("SELECT * FROM divine_schedules WHERE active=1 ORDER BY execute_year,execute_day")],"letters":[dict(r) for r in c.execute("SELECT * FROM divine_letters ORDER BY id DESC LIMIT 30")]}

@app.get("/api/chronicles")
def chronicles(limit:int=30):
    with db() as c: return [dict(r) for r in c.execute("SELECT * FROM chronicles ORDER BY id DESC LIMIT ?",(min(limit,100),))]

@app.get("/api/stats")
def stats():
    catch_up()
    with db() as c:
        return {"people":c.execute("SELECT COUNT(*) n FROM people").fetchone()["n"],"families":c.execute("SELECT COUNT(*) n FROM families").fetchone()["n"],"nobles":c.execute("SELECT COUNT(*) n FROM nobles").fetchone()["n"],"properties":c.execute("SELECT COUNT(*) n FROM properties").fetchone()["n"],"resources":c.execute("SELECT COUNT(*) n FROM resources").fetchone()["n"],"routes":c.execute("SELECT COUNT(*) n FROM routes").fetchone()["n"],"businesses":c.execute("SELECT COUNT(*) n FROM businesses").fetchone()["n"]}

HTML = r'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Reino Fénix</title><style>
*{box-sizing:border-box}body{margin:0;background:#0b1018;color:#edf2f7;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif}header{padding:20px;border-bottom:1px solid #273244;position:sticky;top:0;background:#0b1018eF;backdrop-filter:blur(12px);z-index:2}h1{margin:0 0 5px;font-size:30px}small,.muted{color:#a8b3c4}.wrap{max-width:1100px;margin:auto;padding:18px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px}.card{background:#151d29;border:1px solid #29374b;border-radius:18px;padding:16px;box-shadow:0 8px 30px #0002}.big{font-size:27px;font-weight:800}.tabs{display:flex;gap:8px;overflow:auto;margin:12px 0}.tab,button{border:1px solid #3a4a62;background:#223047;color:#fff;padding:11px 14px;border-radius:12px;font-weight:700}.tab.active{background:#536b8e}.panel{display:none}.panel.active{display:block}.row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}input,select,textarea{width:100%;background:#202c3e;color:#fff;border:1px solid #3c4d66;border-radius:12px;padding:12px;font-size:15px}label{display:block;color:#aeb9c9;margin:8px 0 5px}.field{flex:1;min-width:180px}.danger{background:#51252a}.ok{background:#254d39}.log{white-space:pre-wrap;line-height:1.6}.pill{display:inline-block;padding:4px 8px;border-radius:99px;background:#263750;margin:3px}.error{color:#ff8f8f}.success{color:#8ff0b5}</style></head><body><header><div class="wrap"><h1>🔥 Reino Fénix</h1><small>Universo autónomo · simulación persistente · Modo Dios</small><div id="status" class="muted">Conectando...</div></div></header><main class="wrap"><div class="tabs"><button class="tab active" onclick="show('home',this)">🌍 Mundo</button><button class="tab" onclick="show('people',this)">👥 Personas</button><button class="tab" onclick="show('economy',this)">💰 Economía</button><button class="tab" onclick="show('politics',this)">👑 Política</button><button class="tab" onclick="show('god',this)">👁️ Dios</button><button class="tab" onclick="show('history',this)">📜 Historia</button></div>
<section id="home" class="panel active"><div class="grid" id="stats"></div><div class="card"><h2>Crónica del día</h2><div id="chronicle" class="log">Cargando...</div></div><div class="card"><h2>Control del tiempo</h2><div class="row"><button onclick="advance(1)">+1 día</button><button onclick="advance(7)">+1 semana</button><button onclick="advance(30)">+30 días</button><button onclick="advance(365)">+1 año</button><button onclick="togglePause()">Pausa / Reanudar</button></div><p id="msg" class="muted"></p></div></section>
<section id="people" class="panel"><div class="card"><h2>Habitantes</h2><input id="search" placeholder="Buscar persona..." oninput="loadPeople()"><div id="peopleList"></div></div></section>
<section id="economy" class="panel"><div class="card"><h2>Economía</h2><div id="econ"></div></div></section>
<section id="politics" class="panel"><div class="card"><h2>Reinos y poder</h2><div id="pol"></div></div></section>
<section id="god" class="panel"><div class="card"><h2>👁️ Modo Dios</h2><p class="muted">Los habitantes no conocen tu existencia. Tus intervenciones se registran y sus consecuencias entran en la causalidad del mundo.</p><div class="grid"><div class="field"><label>Acción</label><select id="action" onchange="renderGod()"><option value="wealth">💰 Dar riqueza</option><option value="kill">☠️ Matar</option><option value="save">✨ Salvar</option><option value="health">❤️ Cambiar salud</option><option value="relation">🤝 Cambiar relación</option><option value="reveal">🧠 Revelar información</option><option value="erase">🕳️ Borrar información</option><option value="letter">✉️ Enviar carta</option><option value="weather">🌦️ Cambiar clima</option><option value="resource">⛏️ Crear recursos</option><option value="conflict">⚔️ Crear conflicto</option></select></div></div><div id="godFields"></div><button onclick="godAction()">⚡ Ejecutar intervención</button><div id="godMsg"></div></div></section>
<section id="history" class="panel"><div class="card"><h2>Historia registrada</h2><div id="hist"></div></div></section></main><script>
let W=null, people=[]; const $=id=>document.getElementById(id); async function api(u,o={}){let r=await fetch(u,{headers:{'Content-Type':'application/json'},...o});let t=await r.text();if(!r.ok)throw new Error(t);return t?JSON.parse(t):{}}
function show(id,b){document.querySelectorAll('.panel').forEach(x=>x.classList.remove('active'));$(id).classList.add('active');document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));b.classList.add('active');if(id==='people')loadPeople();if(id==='economy')loadEconomy();if(id==='politics')loadPolitics();if(id==='god'){loadPeople();renderGod()}if(id==='history')loadHistory()}
async function load(){try{W=await api('/api/world');render();$('status').textContent='● Motor conectado';$('status').className='success'}catch(e){$('status').textContent='⚠️ '+e.message;$('status').className='error'}}
function render(){let w=W; $('stats').innerHTML=`<div class=card><div class=muted>Tiempo</div><div class=big>Año ${w.year}</div><div>Día ${w.day}</div></div><div class=card><div class=muted>Población</div><div class=big>${w.population.toLocaleString()}</div></div><div class=card><div class=muted>Riqueza media</div><div class=big>${Math.round(w.avg_wealth)} 🪙</div></div><div class=card><div class=muted>Conflictos activos</div><div class=big>${w.conflicts.length}</div></div>`;$('chronicle').textContent=w.chronicle||'Sin crónica';$('msg').textContent=w.paused?'⏸️ Simulación pausada':'▶️ Simulación activa'}
async function advance(d){try{W=await api('/api/advance',{method:'POST',body:JSON.stringify({days:d})});render();$('msg').textContent='Avance completado: '+d+' día(s).'}catch(e){$('msg').textContent='❌ '+e.message}}
async function togglePause(){try{W=W.paused?await api('/api/resume',{method:'POST'}):await api('/api/pause',{method:'POST'});render()}catch(e){$('msg').textContent='❌ '+e.message}}
async function loadPeople(){try{people=await api('/api/people?q='+encodeURIComponent($('search')?.value||'')+'&limit=150');let s=people.map(p=>`<div class="card"><b>${p.name}</b> · ${p.age} años ${p.alive?'🟢':'⚫'}<br><span class=pill>${p.role}</span><span class=pill>${p.trait}</span><span class=pill>💰 ${p.wealth}</span><span class=pill>❤️ ${Math.round(p.health)}</span><br><small>ID ${p.id}</small></div>`).join('');$('peopleList').innerHTML=s}catch(e){$('peopleList').textContent=e.message}}
function personOptions(){return people.map(p=>`<option value="${p.id}">${p.name} · ID ${p.id}${p.alive?'':' · muerto'}</option>`).join('')}
function renderGod(){let a=$('action').value, f=''; if(['wealth','kill','save','health','reveal','erase','letter'].includes(a))f+=`<label>Persona</label><select id="gperson">${personOptions()}</select>`; if(a==='wealth')f+=`<label>Cantidad de oro</label><input id="amount" type=number min=1 value=200>`;if(a==='health')f+=`<label>Salud (0–100)</label><input id="health" type=number min=0 max=100 value=100>`;if(['reveal','erase'].includes(a))f+=`<label>Información</label><textarea id="fact" placeholder="Ej.: Su hermano está endeudado con el mercader del puerto."></textarea>`;if(a==='letter')f+=`<div class=grid><div><label>Remitente aparente</label><input id="sender" value="Una voz desconocida"></div><div><label>Mensaje</label><textarea id="body"></textarea></div></div>`;if(a==='relation')f+=`<div class=grid><div><label>Persona A</label><select id="a">${personOptions()}</select></div><div><label>Persona B</label><select id="b">${personOptions()}</select></div></div><label>Tipo de relación</label><input id="kind" value="amistad"><label>Fuerza (-100 a 100)</label><input id="strength" type=number min=-100 max=100 value=50>`;if(a==='weather')f+=`<label>Ciudad (0 = todas)</label><select id="city"><option value=0>Todas</option>${(W?.cities||[]).map(c=>`<option value=${c.id}>${c.name}</option>`).join('')}</select><label>Clima</label><select id="weather"><option>lluvia</option><option>sequía</option><option>tormenta</option><option>nieve</option><option>calor extremo</option><option>niebla</option></select><label>Intensidad</label><input id="intensity" type=number min=1 max=100 value=60><label>Duración en días</label><input id="duration" type=number min=1 value=3>`;if(a==='resource')f+=`<label>Ciudad</label><select id="city">${(W?.cities||[]).map(c=>`<option value=${c.id}>${c.name}</option>`).join('')}</select><label>Recurso</label><select id="resource">${['grano','madera','hierro','carbón','piedra','lana','ganado','pescado','sal','vino','herramientas'].map(x=>`<option>${x}</option>`).join('')}</select><label>Cantidad</label><input id="quantity" type=number min=1 value=100>`;if(a==='conflict')f+=`<div class=grid><div><label>Nombre</label><input id="name" value="Nueva disputa"></div><div><label>Intensidad</label><input id="intensity" type=number min=1 max=100 value=50></div></div><label>Lado A</label><input id="sidea" value="Facción A"><label>Lado B</label><input id="sideb" value="Facción B"><label>Causa</label><textarea id="cause">Una disputa que los habitantes intentarán explicar según la información que posean.</textarea>`;$('godFields').innerHTML=f}
async function godAction(){let a=$('action').value,p={};let target_type='world',target_id=0;if(['wealth','kill','save','health','reveal','erase','letter'].includes(a)){target_type='person';target_id=+$('gperson').value}if(a==='wealth')p={amount:+$('amount').value};if(a==='health')p={health:+$('health').value};if(a==='reveal'||a==='erase')p={fact:$('fact').value};if(a==='letter')p={sender:$('sender').value,body:$('body').value};if(a==='relation')p={person_a:+$('a').value,person_b:+$('b').value,kind:$('kind').value,strength:+$('strength').value};if(a==='weather')p={city_id:+$('city').value,weather:$('weather').value,intensity:+$('intensity').value,duration:+$('duration').value};if(a==='resource')p={city_id:+$('city').value,resource:$('resource').value,quantity:+$('quantity').value};if(a==='conflict')p={name:$('name').value,side_a:$('sidea').value,side_b:$('sideb').value,intensity:+$('intensity').value,cause:$('cause').value};try{let r=await api('/api/divine/intervene',{method:'POST',body:JSON.stringify({action:a,target_type,target_id,parameters:p,description:'Intervención manual desde Modo Dios'})});W=r.world;render();$('godMsg').innerHTML='<p class=success>✅ '+r.consequence+'</p>'}catch(e){$('godMsg').innerHTML='<p class=error>❌ '+e.message+'</p>'}}
async function loadEconomy(){let l=await api('/api/layers');$('econ').innerHTML=`<p><b>${l.businesses.length}</b> negocios activos · <b>${l.resources.length}</b> mercados de recursos · <b>${l.routes.length}</b> rutas</p>`+l.resources.slice(0,24).map(r=>`<span class=pill>${r.resource}: ${r.quantity} · ${r.price.toFixed(1)} 🪙</span>`).join('')}
async function loadPolitics(){let l=await api('/api/layers');$('pol').innerHTML=l.factions.map(f=>`<span class=pill>${f.name} · influencia ${f.influence}</span>`).join('')+`<p>40 nobles · ${l.offices.length} cargos · ${l.families} familias · ${l.properties} propiedades</p>`}
async function loadHistory(){let h=await api('/api/chronicles?limit=20');$('hist').innerHTML=h.map(x=>`<div class=card><b>Año ${x.year}, día ${x.day}</b><div class=log>${x.text}</div></div>`).join('')}
load();setInterval(load,30000);
</script></body></html>'''

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app",host="127.0.0.1",port=8000,reload=False)
