#!/usr/bin/env python3
"""Field Atlas add-on: run from the atlas folder. No third-party dependencies."""
import argparse, datetime as dt, json, math, os, re, shutil, tempfile
from pathlib import Path

ROOT = Path.cwd()
JS = ROOT/'static/app.js'; STORE = ROOT/'static/operator-heights.json'; CATALOG = ROOT/'data/nodes.json'
TAG='// FIELD ATLAS: OPERATOR HEIGHTS v1'
FEATURE = r'''
// FIELD ATLAS: OPERATOR HEIGHTS v1
let operatorHeights = {}, heightsAvailable = true;
async function loadOperatorHeights(){
  try { const resp=await fetch('/static/operator-heights.json',{cache:'no-store'});if(!resp.ok)throw Error('unavailable');const data=await resp.json();if(!data||Array.isArray(data)||typeof data!=='object')throw Error('invalid');operatorHeights=data;heightsAvailable=true; }
  catch {operatorHeights={};heightsAvailable=false;}
}
function heightRecord(n){const h=operatorHeights[n?.id?.toLowerCase()];return h && Number.isFinite(h.metres) && h.metres>=0 && h.metres<=1000 ? h:null;}
function showHeightSource(n,manual=false){
 let box=document.getElementById('heightSource');if(!box){box=document.createElement('div');box.id='heightSource';box.className='hint';box.style.marginTop='8px';let anchor=document.getElementById('hb').closest('.heights');let note=anchor.nextElementSibling;if(note?.textContent.includes('Node height is assumed'))note.textContent='Both antenna heights are metres above local ground.';anchor.parentNode.insertBefore(box,note?note.nextSibling:anchor.nextSibling);}
 box.replaceChildren();let r=heightRecord(n);let text=manual?'Manual scenario · not saved':r?`Operator reported · ${r.metres} m above ground${r.date?' · '+r.date:''}`:`Assumed · 6 m above ground${heightsAvailable?' (no report on file)':' (height file unavailable)'}`;
 box.append(document.createTextNode(`${n.name}: ${text}. `));if(manual){let reset=document.createElement('button');reset.type='button';reset.textContent=r?'Use reported height':'Use assumed height';reset.onclick=()=>{applyNodeHeight(n);draw()};box.append(reset)}
}
function applyNodeHeight(n){$('hb').value=heightRecord(n)?.metres??6;showHeightSource(n);}
'''
def stop(msg): raise SystemExit(msg)
def atomic(path,text):
 fd,name=tempfile.mkstemp(dir=path.parent,prefix='.'+path.name+'.');tmp=Path(name)
 try:
  with os.fdopen(fd,'w',encoding='utf-8') as out:out.write(text)
  tmp.chmod(path.stat().st_mode & 0o777 if path.exists() else 0o644);os.replace(tmp,path)
 finally:tmp.unlink(missing_ok=True)
def save(data):atomic(STORE,json.dumps(data,indent=2,sort_keys=True,allow_nan=False)+'\n')
def store():
 if not STORE.exists():stop('Run the install command first.')
 data=json.loads(STORE.read_text());
 if not isinstance(data,dict):stop('Invalid height file. Nothing changed.')
 return data
def install():
 s=JS.read_text()
 if TAG in s:print('The height add-on is already installed.');return
 changes=[('function applyCatalogue(c){',FEATURE+'\nfunction applyCatalogue(c){'),('selected=n;selectedKey=n.id;profile=null;', 'selected=n;selectedKey=n.id;applyNodeHeight(n);profile=null;'),("$('ha').oninput=$('hb').oninput=draw;","$('ha').oninput=draw;$('hb').oninput=()=>{if(selected)showHeightSource(selected,true);draw()};"),("applyCatalogue(await json('/api/catalogue'))","await loadOperatorHeights();applyCatalogue(await json('/api/catalogue'))"),("applyCatalogue(await json('/api/update',{method:'POST'}))","await loadOperatorHeights();applyCatalogue(await json('/api/update',{method:'POST'}))")]
 for a,b in changes:
  if s.count(a)!=1:stop('This app.js differs from the expected version. Nothing was changed.');
  s=s.replace(a,b)
 if STORE.exists():store()
 backup=ROOT/'height-add-on-backups'/dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f');backup.mkdir(parents=True);shutil.copy2(JS,backup/'app.js');
 if not STORE.exists():save({})
 atomic(JS,s);print('Installed. Hard-refresh the atlas. Original JavaScript saved to',backup/'app.js')
def choose(query):
 nodes=json.loads(CATALOG.read_text());q=query.strip().casefold()
 if not q:stop('Supply a node name or its full public key.')
 matches=[n for n in nodes if str(n[5]).casefold()==q] or [n for n in nodes if q in str(n[0]).casefold()]
 if not matches:stop('No matching node in data/nodes.json. Try a shorter name or refresh the catalogue.')
 if len(matches)>40:stop(f'{len(matches)} matches. Use a more specific node name or the full public key.')
 for i,n in enumerate(matches,1):print(f'{i}. {n[0]} | {n[4]} | {n[1]}, {n[2]} | {n[5]}')
 pick=input('Select number (Enter to cancel): ').strip() if len(matches)>1 else '1'
 if not pick.isdigit() or not 1<=int(pick)<=len(matches):stop('Cancelled; nothing changed.')
 return matches[int(pick)-1]
def main():
 parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='cmd',required=True);sub.add_parser('install');p=sub.add_parser('set',help='Save an operator-reported antenna height in metres above local ground');p.add_argument('node');p.add_argument('metres',type=float);p.add_argument('--date',type=dt.date.fromisoformat,default=dt.date.today(),help='Date of report, YYYY-MM-DD; defaults to today');p=sub.add_parser('remove');p.add_argument('node');sub.add_parser('list');args=parser.parse_args()
 if not JS.is_file() or not CATALOG.is_file():stop('First cd into the UK-MeshCore-Atlas folder containing server.py.')
 if args.cmd=='install':install();return
 data=store()
 if args.cmd=='list':
  for key,h in data.items():print(h['name'],str(h['metres'])+' m',h['date'],key,sep=' | ')
  print(f'{len(data)} reported height(s).');return
 if args.cmd=='set' and not(math.isfinite(args.metres) and 0<=args.metres<=1000):stop('Height must be 0 to 1000 metres above local ground.')
 n=choose(args.node);key=str(n[5]).lower()
 if not re.fullmatch('[0-9a-f]{64}',key):stop('Invalid public key. Nothing changed.')
 if args.cmd=='remove' and key not in data:stop('No saved report for that node.')
 msg=f'Save {args.metres:g} m above local ground for {n[0]}?' if args.cmd=='set' else f'Remove the report for {n[0]}?'
 if input(msg+' [y/N] ').strip().lower() not in ('y','yes'):stop('Cancelled; nothing changed.')
 if args.cmd=='remove':del data[key]
 else:data[key]={'metres':args.metres,'date':args.date.isoformat(),'name':str(n[0])}
 save(data);print('Saved. Reload the atlas to see the change.')
if __name__=='__main__':main()
