'use strict';
// Same effective Earth radius and endpoint-inclusive samples as the profile chart.
function atlasClearance({d, z}, a, b) {
  if (![d,a,b].every(Number.isFinite) || d<0 || a<0 || b<0 || !Array.isArray(z) || z.length<2 || !z.every(Number.isFinite)) throw Error('Invalid terrain or height');
  const last=z.length-1; let gap=Infinity, at=0;
  for (let i=0;i<=last;i++) {
    const q=i/last;
    const line=(1-q)*(z[0]+a)+q*(z[last]+b)-d*d*q*(1-q)/(2*6371000*4/3);
    if (line-z[i]<gap) {gap=line-z[i]; at=d*q;}
  }
  return {gap,at};
}
if (typeof module!=='undefined' && module.exports) module.exports={atlasClearance};
if (typeof document!=='undefined') (()=>{
  const storeKey='field-atlas.observations.v1';
  const outcomes=['Heard only','Direct reply (verified)','Reply via mesh','Reply (route unknown)','No reply'];
  const el=(tag,text)=>{const x=document.createElement(tag);if(text!=null)x.textContent=text;return x;};
  const button=(txt,fn)=>{const b=el('button',txt);b.type='button';b.onclick=fn;return b;};
  const style=el('style');style.textContent=`#fieldPanel{width:min(940px,95vw);max-height:88vh}.ft-tools{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0}.ft-scroll{overflow:auto;max-height:50vh}.ft-table{width:100%;border-collapse:collapse;font-size:13px}.ft-table th,.ft-table td{text-align:left;border-bottom:1px solid var(--edge);padding:6px}.ft-table th{background:var(--paper);position:sticky;top:0}.ft-table button{text-align:left}.ft-table .pass{color:#28583d}.ft-table .block{color:#973e25}#fieldPanel summary{cursor:pointer}`;document.head.append(style);
  const tools=el('div');tools.className='ft-tools';const host=$('originstatus');host.after(tools);tools.append(button('Compare nearby repeaters',compare),button('Field-test log',log));
  const dlg=el('dialog');dlg.id='fieldPanel';dlg.setAttribute('aria-labelledby','fieldTitle');document.body.append(dlg);
  let cancel=null;let cacheOrigin='',cache=new Map();
  function panel(title){cancel?.abort();cancel=new AbortController();dlg.replaceChildren();const heading=el('h2',title);heading.id='fieldTitle';dlg.append(button('Close',()=>dlg.close()),heading);if(!dlg.open)dlg.showModal();return cancel.signal;}
  dlg.addEventListener('close',()=>cancel?.abort());
  function table(headers){const wrap=el('div'),t=el('table'),h=t.createTHead().insertRow(),body=t.createTBody();wrap.className='ft-scroll';t.className='ft-table';headers.forEach(s=>h.append(el('th',s)));wrap.append(t);dlg.append(wrap);return body;}
  const meters=v=>Number(v).toFixed(1)+' m';
  function antenna(id){let v=$(id).valueAsNumber;return Number.isFinite(v)&&v>=0&&v<=1000?v:null;}
  async function compare(){const signal=panel('Compare nearby repeaters');let a=antenna('ha');if(!origin||a===null){dlg.append(el('p','Set an origin postcode and a valid antenna height first.'));return;}
    const o={...origin}, candidates=nodes.filter(n=>n.t===2).sort((a,b)=>a.d-b.d).slice(0,20);
    const key=o.lat+','+o.lon;if(key!==cacheOrigin){cache.clear();cacheOrigin=key;}
    dlg.append(el('p',`${o.pc} · Your antenna ${a} m above ground. Nearest ${candidates.length} repeaters across all directory filters. Ranked by terrain clearance, not expected signal strength.`));
    const msg=el('p','Loading terrain…');msg.setAttribute('role','status');dlg.append(msg);const body=table(['Repeater','Distance','Bearing (true)','Node height','Worst terrain clearance']);
    let next=0,done=0,records=[];
    async function worker(){while(!signal.aborted && next<candidates.length){const n=candidates[next++];try{let k=n.id+':'+n.lat+','+n.lon;let p=cache.get(k);if(!p){p=await json('/api/profile?'+new URLSearchParams({lat:o.lat,lon:o.lon,toLat:n.lat,toLon:n.lon}),{signal});if(signal.aborted)return;cache.set(k,p);}let r=typeof heightRecord==='function'?heightRecord(n):null;const b=r?.metres??6;records.push({n,p,b,source:r?'reported':'assumed',...atlasClearance(p,a,b)});}catch(e){if(signal.aborted)return;records.push({n,error:true});}msg.textContent=`Sampled ${++done} of ${candidates.length} paths…`;}}
    await Promise.all([worker(),worker()]);if(signal.aborted)return;
    records.sort((x,y)=>Number(!!x.error)-Number(!!y.error)||(y.gap-x.gap)||(x.n.d-y.n.d));for(const r of records){const row=body.insertRow();const b=button(r.n.name,()=>{dlg.close();choose(r.n,true);});row.insertCell().append(b);row.insertCell().textContent=dist(r.p?.d??r.n.d);row.insertCell().textContent=r.error?'—':Math.round(r.p.bearing)%360+'°';row.insertCell().textContent=r.error?'—':`${r.b} m · ${r.source}`;let cell=row.insertCell();cell.textContent=r.error?'No profile':r.gap<0?`Blocked by ${meters(-r.gap)}`:`Clear by ${meters(r.gap)}`;cell.className=r.gap<0?'block':'pass';}
    msg.textContent=records.length?`${records.filter(r=>r.gap>=0).length} terrain-clear · ${records.filter(r=>r.gap<0).length} obstructed · ${records.filter(r=>r.error).length} unavailable. Select a repeater to open its profile.`:'No repeaters in this catalogue.';dlg.append(el('p','Minimum includes both endpoints. No Fresnel clearance, building or radio-performance check. Change your antenna height and reopen to compare again.'));
  }
  function load(){const x=JSON.parse(localStorage.getItem(storeKey)||'[]');if(!Array.isArray(x))throw Error('Invalid log');return x;}
  function write(x){localStorage.setItem(storeKey,JSON.stringify(x));}
  function log(){panel('Field-test log');dlg.append(el('p','Saved only in this browser on this site. Entries include your origin postcode. Export before clearing browser data; nothing is sent to the server.'));
    let entries;try{entries=load();}catch{dlg.append(el('p','The browser log cannot be read. Storage may be unavailable.'));return;}
    const msg=el('p');msg.setAttribute('role','status');dlg.append(msg);
    const a=antenna('ha'),b=antenna('hb');if(origin&&selected&&profile&&a!==null&&b!==null){const n=selected,p=profile,o=origin;const {gap}=atlasClearance(p,a,b);let heading=el('b',`${o.pc} → ${n.name}`);dlg.append(heading);const controls=el('div');controls.className='ft-tools';let outcome=el('select');outcome.setAttribute('aria-label','Observation');outcomes.forEach(s=>outcome.add(new Option(s,s)));const notes=el('input');notes.placeholder='Optional field notes';notes.setAttribute('aria-label','Field notes');notes.maxLength=300;
      controls.append(outcome,notes,button('Save observation',()=>{try{const all=load();all.unshift({time:new Date().toISOString(),postcode:o.pc,node:n.name,publicKey:n.id,originHeight:a,nodeHeight:b,distanceM:Math.round(p.d),minClearanceM:+gap.toFixed(2),outcome:outcome.value,notes:notes.value.trim()});write(all);log();}catch{msg.textContent='Could not save locally. Storage may be disabled or full.';}}));dlg.append(controls);
    }else dlg.append(el('p','To add a test, set an origin and select a node with a loaded profile.'));
    dlg.append(el('h3',`${entries.length} saved observation${entries.length===1?'':'s'}`));if(!entries.length)return;
    const bar=el('div');bar.className='ft-tools';bar.append(button('Export log (JSON)',()=>{const u=URL.createObjectURL(new Blob([JSON.stringify(entries,null,2)],{type:'application/json'}));const link=el('a');link.href=u;link.download='field-atlas-observations.json';link.click();setTimeout(()=>URL.revokeObjectURL(u),1000);}),button('Clear log',()=>{if(confirm('Delete all observations stored in this browser? Export first if you want a copy.')){try{write([]);log();}catch{msg.textContent='Could not clear local storage.';}}}));dlg.append(bar);
    const body=table(['When','Origin → node','Outcome','Predicted minimum','Notes']);for(const e of entries){const row=body.insertRow();for(const s of [new Date(e.time).toLocaleString(),`${e.postcode} → ${e.node}`,e.outcome,meters(e.minClearanceM),e.notes])row.insertCell().textContent=s;}
  }
})();
