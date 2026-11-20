#!/usr/bin/env python3
"""Merge an authorised MeshMapper public-key / reported-height CSV into Field Atlas. Preview by default."""
import argparse,csv,datetime as dt,json,math,os,re,shutil,tempfile
from collections import Counter,defaultdict
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('csvfile',type=Path);p.add_argument('--key-column',default='public_key');p.add_argument('--height-column',default='height_agl_m',help='Column containing reported metres above local ground, not altitude');p.add_argument('--apply',action='store_true');a=p.parse_args(); directory=Path('static');store=directory/'operator-heights.json';catalogue=Path('data/nodes.json')
if not catalogue.is_file() or not store.is_file():p.exit(1,'Run from your UK-MeshCore-Atlas folder after installing the operator-height add-on.\n')
nodes={str(row[5]).lower():row[0] for row in json.loads(catalogue.read_text()) if row[3]==2};old=json.loads(store.read_text());assert isinstance(old,dict);existing={k.lower() for k in old};c=Counter();groups=defaultdict(set)
with a.csvfile.open(encoding='utf-8-sig',newline='') as f:
 reader=csv.DictReader(f)
 for column in [a.key_column,a.height_column]:
  if column not in (reader.fieldnames or []):p.exit(1,f'Missing column {column!r}. File headers: {reader.fieldnames}. Specify --key-column and --height-column if needed.\n')
 for row in reader:
  c['CSV rows']+=1;k=(row.get(a.key_column) or '').strip().lower();v=(row.get(a.height_column) or '').strip()
  if not v:c['empty heights']+=1;continue
  if not re.fullmatch('[0-9a-f]{64}',k):c['missing/invalid full key']+=1;continue
  if k not in nodes:c['not a UK atlas repeater match']+=1;continue
  try:h=float(v)
  except ValueError:h=math.nan
  if not math.isfinite(h) or not 0<=h<=1000:c['invalid height']+=1;continue
  groups[k].add(h)
changes={};date=dt.date.today().isoformat()
for k,hs in groups.items():
 if len(hs)!=1:c['conflicting source heights (skipped)']+=1;continue
 if k in existing:c['already recorded (preserved)']+=1;continue
 h=next(iter(hs));changes[k]={'name':nodes[k],'metres':h,'source':'MeshMapper repeater details','date':'','imported_on':date};print(f'{nodes[k]} | {h:g} m AGL | {k}')
for name,count in c.items():print(f'{name}: {count}')
print(f'New matched heights: {len(changes)}')
if not a.apply:print('Preview only. No files changed.');raise SystemExit
if changes:
 backup=Path('height-add-on-backups')/dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f');backup.mkdir(parents=True);shutil.copy2(store,backup/store.name);old.update(changes)
 with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=directory,delete=False) as f:json.dump(old,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n');tmp=Path(f.name)
 tmp.chmod(store.stat().st_mode&0o777);os.replace(tmp,store);print('Saved. Previous records backed up to',backup/store.name)
