from flask import Flask,request,jsonify,send_from_directory,abort
from pathlib import Path
import os,math,json,zipfile,struct,re,requests,threading,time,zlib,msgpack
from functools import lru_cache
from datetime import datetime,timezone
import numpy as np
from scipy.ndimage import map_coordinates
from pyproj import Transformer,Geod
os.chdir(Path(__file__).resolve().parent)
app=Flask(__name__); root=Path('data');zips={s:zipfile.ZipFile(root/(s+'.zip')) for s in ['gb50','ni90','regional','postcodes']};files={s:set(z.namelist()) for s,z in zips.items()};nodes=json.loads((root/'nodes.json').read_text());stamp=(root/'date.txt').read_text().strip() if (root/'date.txt').exists() else '2026-11-20';gb=Transformer.from_crs(4326,27700,always_xy=True);rev=Transformer.from_crs(27700,4326,always_xy=True);geod=Geod(ellps='WGS84');refresh_lock=threading.Lock();last=0
@lru_cache(maxsize=320)
def grid(s,key):
 w={'gb50':200,'ni90':800,'regional':256}[s];return np.frombuffer(zips[s].read(key),'<i2').reshape(-1,w).cumsum(axis=1,dtype=np.int16)
def terrain(lat,lon):
 la=np.atleast_1d(lat);lo=np.atleast_1d(lon);e,n=map(np.asarray,gb.transform(lo,la));val=np.full(len(la),np.nan);typ=np.zeros(len(la),'uint8');
 def sample(src,cols,rows,gx,gy,fmt,scale,tag,ok):
  idx=np.flatnonzero(ok);pairs=np.column_stack((cols[idx],rows[idx])).astype('int32');unique,inv=np.unique(pairs,axis=0,return_inverse=True)
  for i,(u,v) in enumerate(unique):
   key=fmt(u,v)
   if key not in files[src]:continue
   ids=idx[inv==i];xx,yy=scale(gx[ids],gy[ids],u,v);arr=map_coordinates(grid(src,key),[yy,xx],order=1,mode='nearest',output=np.float64);good=arr>-100;val[ids[good]]=arr[good];typ[ids[good]]=tag
 sample('gb50',np.floor(e/10000),np.floor(n/10000),e,n,lambda x,y:f'{x}_{y}',lambda e,n,x,y:((e-x*10000)/50-.5,199.5-(n-y*10000)/50),1,np.ones(len(la),bool));
 sample('ni90',np.floor(lo),np.floor(la),lo,la,lambda x,y:f'{y}_{x}_800',lambda a,b,x,y:((a-x)*800,(1+y-b)*1200),2,np.isnan(val));X=(lo+180)/360*256;Y=(1-np.arcsinh(np.tan(np.radians(la)))/np.pi)*128;sample('regional',np.floor(X),np.floor(Y),X,Y,lambda x,y:f'{x}_{y}',lambda a,b,x,y:((a-x)*256-.5,(b-y)*256-.5),3,np.isnan(val));
 if not np.isfinite(val).all():raise ValueError('Missing terrain coverage')
 return val,typ
@app.get('/')
def index():return send_from_directory('static','index.html')
@app.get('/api/catalogue')
def catalogue():return jsonify(nodes=nodes,date=stamp)
@app.post('/api/update')
def refresh():
 global nodes,stamp,last
 if not refresh_lock.acquire(False):return jsonify(error='A map update is already running.'),429
 try:
  if time.time()-last<900:return catalogue()
  import shapely
  r=requests.get('https://map.meshcore.io/api/v1/nodes?binary=1&short=1',timeout=25);r.raise_for_status();data=msgpack.unpackb(r.content,timestamp=3);gs=shapely.from_wkb(zlib.decompress((root/'scope.wkb').read_bytes())).geoms;names=['England','Northern Ireland','Scotland','Wales'];new=[]
  for g in gs:shapely.prepare(g)
  for a in data:
   x,y=a.get('lon'),a.get('lat');
   if x is None or y is None or not(-9<=x<=2 and 49.7<=y<=61.2):continue
   for k,g in zip(names,gs):
    if shapely.intersects_xy(g,x,y):new.append([a.get('n') or 'Unnamed node',y,x,a['t'],k,a['pk'].hex(),str(a.get('ud') or a.get('id') or '')[:10]]);break
  if not new:raise ValueError('No results')
  temp=root/'new.tmp';temp.write_text(json.dumps(new,separators=(',',':'),ensure_ascii=False));temp.replace(root/'nodes.json');nodes=new;stamp=datetime.now(timezone.utc).date().isoformat();(root/'date.txt').write_text(stamp);last=time.time();return catalogue()
 except Exception:return jsonify(error='MeshCore update unavailable. The saved catalogue is still usable.'),503
 finally:refresh_lock.release()
@lru_cache(maxsize=256)
def postcode(pc):
 area,end=pc[:-3],pc[-3:].encode();
 if area in files['postcodes']:
  for code,e,n in struct.iter_unpack('<3sii',zips['postcodes'].read(area)):
   if code==end:
    lon,lat=rev.transform(e,n);return lat,lon
 r=requests.get('https://api.postcodes.io/postcodes/'+pc,timeout=9);
 if r.status_code in (400,404):raise ValueError()
 r.raise_for_status();obj=r.json()['result'];return obj['latitude'],obj['longitude']
@app.get('/api/origin')
def origin():
 pc=''.join(request.args.get('q','').upper().split());
 if not re.fullmatch(r'[A-Z]{1,2}\d[A-Z\d]?\d[A-Z]{2}',pc):return jsonify(error='Enter a full UK postcode, for example RG12 9PW.'),400
 try:lat,lon=postcode(pc);h,src=terrain(lat,lon);return jsonify(pc=pc[:-3]+' '+pc[-3:],lat=lat,lon=lon,ground=round(h[0],1),src=int(src[0]))
 except ValueError:return jsonify(error='No mapped UK postcode found. Check the postcode and try again.'),404
 except Exception:return jsonify(error='Postcode lookup is temporarily unavailable. Please try again.'),503
@app.get('/api/profile')
def profile():
 try:
  a,b,c,d=[float(request.args[k]) for k in ['lat','lon','toLat','toLon']];assert all(math.isfinite(x) for x in (a,b,c,d)) and 49.6<=min(a,c)<=max(a,c)<=61.2 and -9<=min(b,d)<=max(b,d)<=2.2
  az,_,length=geod.inv(b,a,d,c);count=max(2,math.ceil(length/50)+1);ds=np.linspace(0,length,count);xs,ys,_=geod.fwd(np.full(count,b),np.full(count,a),np.full(count,az),ds);v,src=terrain(ys,xs);idx=np.unique(np.round(np.linspace(0,count-1,min(count,100))).astype(int));return jsonify(d=length,z=np.round(v,1).tolist(),line=np.column_stack([ys[idx],xs[idx]]).round(5).tolist(),sources=list(map(int,np.unique(src))),bearing=(az+360)%360)
 except Exception:return jsonify(error='No complete terrain profile could be calculated for these coordinates.'),400
# Detailed local relief tiles are drawn from the same elevation grids as the profile.
@lru_cache(maxsize=256)
def relief(z,x,y):
 from PIL import Image
 import io
 size=128; q=(np.arange(size)+.5)/size;lng,lat=np.meshgrid((x+q)/2**z*360-180,np.degrees(np.arctan(np.sinh(np.pi*(1-2*(y+q)/2**z)))));h,_=terrain(lat.ravel(),lng.ravel());h=h.reshape(size,size);mpp=40075017*np.cos(np.radians(lat.mean()))/2**z/size;dy,dx=np.gradient(h);shade=(.38*dx-.46*dy)/max(mpp,1);levels=[0,60,130,270,500,900,1300];colors=np.array([[227,232,209],[218,226,193],[199,214,177],[181,195,161],[166,176,151],[163,159,142],[168,169,161]]);rgb=np.stack([np.interp(h,levels,colors[:,j]) for j in range(3)],axis=2)*(1+np.clip(shade,-.26,.22))[:,:,None];rgb[h==0]=[202,219,222];buf=io.BytesIO();Image.fromarray(rgb.clip(0,255).astype('uint8')).save(buf,format='JPEG',quality=84);return buf.getvalue()
@app.get('/relief/<int:z>/<int:x>/<int:y>.jpg')
def tile(z,x,y):
 from flask import Response
 if not 9<=z<=16:abort(404)
 try:return Response(relief(z,x,y),mimetype='image/jpeg',headers={'Cache-Control':'public, max-age=86400'})
 except ValueError:abort(404)
if __name__=='__main__':app.run(host='127.0.0.1',port=int(os.getenv('PORT','8080')),threaded=True)
