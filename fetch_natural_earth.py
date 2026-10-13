"""Download the four Natural Earth 1:10m archives required by spatial.py.
Run once from a networked environment, then ./run_all.sh regenerates maps too.
"""
from pathlib import Path
from urllib.request import urlretrieve
from zipfile import ZipFile
HERE=Path(__file__).resolve().parent
sets=[('10m_physical','ne_10m_land'),('10m_cultural','ne_10m_admin_0_countries'),('10m_physical','ne_10m_bathymetry_K_200'),('10m_physical','ne_10m_bathymetry_J_1000')]
for group,name in sets:
 d=HERE/'data'/'naturalearth'/group; d.mkdir(parents=True,exist_ok=True)
 if (d/f'{name}.shp').exists(): print(name,'already present'); continue
 url=f'https://naturalearth.s3.amazonaws.com/{group}/{name}.zip'; z=HERE/'data'/'naturalearth'/f'{name}.zip'
 print('downloading',url); urlretrieve(url,z)
 with ZipFile(z) as f: f.extractall(d)
 z.unlink(); print('installed',name)
