"""Install only the required data files from the original Field Atlas distribution."""
from pathlib import Path
import argparse, shutil, tempfile, zipfile
p=argparse.ArgumentParser(description=__doc__);p.add_argument('archive',type=Path);a=p.parse_args()
root=Path(__file__).resolve().parents[1];dest=root/'data';names=('gb50.zip','ni90.zip','regional.zip','postcodes.zip','scope.wkb','nodes.json');
if dest.exists():p.exit(1,'data/ already exists; refusing to overwrite a live catalogue.\n')
with zipfile.ZipFile(a.archive) as z,tempfile.TemporaryDirectory(dir=root) as td:
 tmp=Path(td)/'data';tmp.mkdir();
 for n in names:
  with z.open('UK-MeshCore-Atlas/data/'+n) as src,(tmp/n).open('wb') as out:shutil.copyfileobj(src,out)
 tmp.rename(dest)
print('Installed terrain, postcode and node data.')
