"""Spanish marine space for kelp and offshore wind: depth, regions, shipping and fishing constraints.

Data
  Natural Earth 10m: land, 200 m and 1000 m bathymetry, admin-0 countries (public domain).
  Benden (2022) Global Shipping Lanes v1, doi:10.5281/zenodo.6361763 (CC BY 4.0) - schematic routes.
  Traffic separation schemes (TSS): approximate rectangles placed on the IMO-adopted schemes
    off Finisterre, the Strait of Gibraltar, Cabo de Gata and the Canary Islands (positions approximate).
  Port approaches: 10-15 km radius around the main commercial ports.
  Fishing: a rule-based proxy (not observed effort):
    0-6 nm from the coast         -> artisanal fishing, shellfish beds, mussel rafts (high conflict)
    6 nm to the 1000 m isobath    -> trawl, purse-seine and longline grounds on shelf and upper slope
    beyond 1000 m                 -> pelagic longline / deep fisheries (low conflict for moored structures)
  Observed effort (e.g. Global Fishing Watch 0.1-degree fishing hours) can replace the proxy in fish[] below.

Method
  0.025-degree grid. Ocean cells are assigned to the nearest country (equidistance approximation) and
  limited to 200 nm from that country's coast (EEZ approximation). Distances are computed in
  EPSG:3035 (Peninsula, Balearics) or EPSG:32628 (Canaries).
"""
import json
from pathlib import Path

import numpy as np
import shapefile
import shapely
from shapely.geometry import shape, Point, box
from shapely.ops import unary_union, transform
import warnings; warnings.filterwarnings('ignore', category=DeprecationWarning)
from pyproj import Transformer

HERE = Path(__file__).resolve().parent
import os
NE = Path(os.environ.get("NATURAL_EARTH_DIR", str(Path(__file__).resolve().parent / "data" / "naturalearth")))
LANES = HERE / "data/shiplanes/repo/data/Shipping-Lanes-v1/Shipping-Lanes-v1"
OUT = HERE / "outputs"
OUT.mkdir(exist_ok=True)
NM = 1.852

# ---------------------------------------------------------------- inputs
def load(path, bbox):
    r = shapefile.Reader(str(path))
    flds = [f[0] for f in r.fields[1:]]
    out = []
    for sr in r.iterShapeRecords():
        g = shape(sr.shape.__geo_interface__)
        if g.intersects(bbox):
            out.append((dict(zip(flds, sr.record)), g.intersection(bbox)))
    return out

PORTS = {  # name: (lat, lon, approach radius km)
    "Algeciras": (36.13, -5.43, 15), "Valencia": (39.44, -0.30, 15), "Barcelona": (41.34, 2.17, 15),
    "Bilbao": (43.37, -3.06, 15), "Las Palmas": (28.14, -15.40, 15), "Cartagena": (37.57, -0.98, 12),
    "Tarragona": (41.08, 1.23, 12), "Huelva": (37.08, -6.95, 12), "A Coruna": (43.38, -8.38, 12),
    "Vigo": (42.22, -8.80, 12), "Ferrol": (43.45, -8.30, 10), "Gijon": (43.57, -5.69, 12),
    "Santander": (43.46, -3.77, 10), "Pasaia": (43.34, -1.93, 10), "Cadiz": (36.54, -6.30, 10),
    "Malaga": (36.70, -4.41, 10), "Motril": (36.71, -3.52, 10), "Almeria": (36.82, -2.47, 10),
    "Carboneras": (36.97, -1.89, 10), "Alicante": (38.33, -0.48, 10), "Castellon": (39.96, -0.01, 10),
    "Sagunto": (39.64, -0.20, 10), "Palma": (39.55, 2.63, 12), "Ibiza": (38.90, 1.45, 10),
    "Mahon": (39.88, 4.30, 10), "S.C. Tenerife": (28.47, -16.23, 12), "Arrecife": (28.95, -13.53, 10),
    "Pto. Rosario": (28.49, -13.85, 10), "Ceuta": (35.89, -5.31, 10), "Melilla": (35.29, -2.93, 10),
    "Aviles": (43.59, -5.93, 10), "Marin": (42.40, -8.70, 8),
}

# Approximate TSS footprints: (centre lat, centre lon, length km, width km, heading deg from north)
TSS = {
    "Finisterre TSS": (43.10, -9.98, 80, 38, 20),
    "Strait of Gibraltar TSS": (35.95, -5.68, 50, 12, 90),
    "Cabo de Gata TSS": (36.55, -1.98, 45, 20, 45),
    "Canaries TSS (Gran Canaria-Tenerife)": (28.10, -15.95, 70, 18, 0),
    "Canaries TSS (Gran Canaria-Fuerteventura)": (28.25, -14.62, 70, 18, 0),
}

DOMAINS = {
    "peninsula": dict(bbox=(-14.5, 33.0, 6.5, 46.5), crs="EPSG:3035"),
    "canaries": dict(bbox=(-21.5, 25.0, -11.0, 31.5), crs="EPSG:32628"),
}


def region_of(lat, lon, dom):
    """Spanish marine demarcations (Ley 41/2010), approximated by simple boundaries."""
    if dom == "canaries":
        return np.full(lat.shape, "Canaria", dtype=object)
    r = np.full(lat.shape, "Levantino-Balear", dtype=object)
    r[(lat >= 41.85) & (lon <= -1.5)] = "Noratlantica"
    r[(lat < 37.6) & (lon < -6.0) & (lon >= -7.6)] = "Sudatlantica"
    r[(lat < 37.6) & (lon >= -6.0) & (lon < -2.15)] = "Estrecho-Alboran"
    r[(lat < 36.0) & (lon >= -6.0) & (lon < -2.0)] = "Estrecho-Alboran"  # Ceuta, Melilla, Alboran island
    return r


def rect(lat, lon, L, W, hdg, to_m, to_ll):
    x, y = to_m.transform(lon, lat)
    h = np.radians(hdg)
    ux, uy = np.sin(h), np.cos(h)          # along-track
    vx, vy = np.cos(h), -np.sin(h)         # cross-track
    pts = []
    for a, b in ((1, 1), (1, -1), (-1, -1), (-1, 1)):
        pts.append((x + a * ux * L * 500 + b * vx * W * 500, y + a * uy * L * 500 + b * vy * W * 500))
    return shapely.Polygon(pts)


def bathymetry(name):
    """Natural Earth bathymetry layer: the per-layer download places it directly in 10m_physical/,
    the full physical bundle in 10m_physical/ne_10m_bathymetry_all/. Accept either."""
    for sub in ("10m_physical", "10m_physical/ne_10m_bathymetry_all"):
        stem = NE / sub / f"ne_10m_bathymetry_{name}"
        if stem.with_suffix(".shp").exists():
            return stem
    raise FileNotFoundError(f"ne_10m_bathymetry_{name}.shp not found under {NE}; run fetch_natural_earth.py")


def run():
    results, layers = {}, {}
    for dom, cfg in DOMAINS.items():
        bb = box(*cfg["bbox"])
        to_m = Transformer.from_crs("EPSG:4326", cfg["crs"], always_xy=True)
        to_ll = Transformer.from_crs(cfg["crs"], "EPSG:4326", always_xy=True)
        fm = lambda g: transform(to_m.transform, g)
        fl = lambda g: transform(to_ll.transform, g)

        land = unary_union([g for _, g in load(NE / "10m_physical/ne_10m_land", bb)])
        d200 = unary_union([g for _, g in load(bathymetry("K_200"), bb)])
        d1000 = unary_union([g for _, g in load(bathymetry("J_1000"), bb)])
        ctry = [(r["ADM0_A3"], g) for r, g in load(NE / "10m_cultural/ne_10m_admin_0_countries", bb)]
        names = np.array([c for c, _ in ctry])
        cgeom_m = [fm(g.simplify(0.005)) for _, g in ctry]
        esp_m = unary_union([g for c, g in zip(names, cgeom_m) if c == "ESP"])

        # shipping lanes (projected buffers)
        half = {"Major": 10e3, "Middle": 6e3, "Minor": 3e3}
        lane_polys = []
        for rec, g in load(LANES, bb):
            lane_polys.append(fm(g).buffer(half.get(rec.get("Type", "Minor"), 3e3)))
        tss_m = [rect(*v, to_m, to_ll) for k, v in TSS.items()
                 if bb.contains(Point(v[1], v[0]))]
        port_m = [Point(*to_m.transform(lon, lat)).buffer(r * 1e3) for lat, lon, r in PORTS.values()
                  if bb.contains(Point(lon, lat))]
        ship_m = unary_union(lane_polys + tss_m + port_m)

        # grid
        step = 0.025
        x0, y0, x1, y1 = cfg["bbox"]
        lons = np.arange(x0 + step / 2, x1, step)
        lats = np.arange(y0 + step / 2, y1, step)
        LON, LAT = np.meshgrid(lons, lats)
        lon, lat = LON.ravel(), LAT.ravel()
        cell = (step * 111.32 * np.cos(np.radians(lat))) * (step * 110.57)
        ocean = ~shapely.contains_xy(land, lon, lat)
        lon, lat, cell = lon[ocean], lat[ocean], cell[ocean]
        X, Y = to_m.transform(lon, lat)
        pts = shapely.points(X, Y)
        tree = shapely.STRtree(cgeom_m)
        idx = tree.query_nearest(pts, return_distance=False, all_matches=False)
        nearest = names[idx[1][np.argsort(idx[0])]] if idx.ndim == 2 else names[idx]
        dist_esp = shapely.distance(esp_m, pts) / 1e3
        keep = (nearest == "ESP") & (dist_esp <= 370.4)
        lon, lat, cell, X, Y, pts, dist_esp = (a[keep] for a in (lon, lat, cell, X, Y, pts, dist_esp))
        depth = np.where(shapely.contains_xy(d1000, lon, lat), ">1000",
                         np.where(shapely.contains_xy(d200, lon, lat), "200-1000", "0-200"))
        ship = shapely.contains_xy(ship_m, X, Y)
        inshore = dist_esp <= 6 * NM
        fish = np.where(inshore, "artisanal_0-6nm",
                        np.where(depth == ">1000", "deep_low", "trawl_seine_longline"))
        reg = region_of(lat, lon, dom)

        rows = []
        for i in range(len(lon)):
            rows.append((reg[i], depth[i], bool(ship[i]), fish[i], cell[i]))
        results[dom] = rows
        layers[dom] = dict(lon=lon, lat=lat, depth=depth, ship=ship, fish=fish, reg=reg,
                           land=land, ship_ll=fl(ship_m), tss_ll=[fl(t) for t in tss_m],
                           lanes_ll=[fl(l) for l in lane_polys], dist=dist_esp)
    return results, layers


def summarise(results):
    tab = {}
    for dom, rows in results.items():
        for reg, dep, ship, fish, a in rows:
            t = tab.setdefault(reg, {})
            k = f"{dep}|{'ship' if ship else 'noship'}|{fish}"
            t[k] = t.get(k, 0.0) + a
    summ = {}
    for reg, t in tab.items():
        s = {"total": sum(t.values())}
        for dep in ("0-200", "200-1000", ">1000"):
            s[f"depth_{dep}"] = sum(v for k, v in t.items() if k.startswith(dep + "|"))
            s[f"depth_{dep}_outside_shipping"] = sum(v for k, v in t.items() if k.startswith(dep + "|noship"))
            s[f"depth_{dep}_outside_shipping_beyond_6nm"] = sum(
                v for k, v in t.items() if k.startswith(dep + "|noship") and not k.endswith("artisanal_0-6nm"))
        s["shipping_constrained"] = sum(v for k, v in t.items() if "|ship|" in k)
        s["artisanal_0-6nm"] = sum(v for k, v in t.items() if k.endswith("artisanal_0-6nm"))
        summ[reg] = {k: round(v, 0) for k, v in s.items()}
    tot = {}
    for s in summ.values():
        for k, v in s.items():
            tot[k] = tot.get(k, 0) + v
    summ["Spain"] = tot
    return summ


def candidates(layers, max_km=100.0):
    """Kelp and wind+kelp candidate areas (km2) per region: outside shipping, beyond 6 nm, within max_km of coast."""
    out = {}
    for dom, d in layers.items():
        cell = (0.025 * 111.32 * np.cos(np.radians(d["lat"]))) * (0.025 * 110.57)
        ok = (~d["ship"]) & (d["fish"] != "artisanal_0-6nm") & (d["dist"] <= max_km)
        for reg in np.unique(d["reg"]):
            r = d["reg"] == reg
            out[reg] = {
                "shelf_0_200_free": float(cell[r & ok & (d["depth"] == "0-200")].sum()),
                "slope_200_1000_free": float(cell[r & ok & (d["depth"] == "200-1000")].sum()),
            }
    return out


if __name__ == "__main__":
    import pickle
    res, layers = run()
    summ = summarise(res)
    json.dump(summ, open(OUT / "marine_space_by_region.json", "w"), indent=1)
    pickle.dump(layers, open(OUT / "_layers.pkl", "wb"))
    cand = candidates(layers)
    json.dump(cand, open(OUT / "candidate_areas.json", "w"), indent=1)
    print(json.dumps(cand, indent=1))
    for r, s in summ.items():
        print(r, {k: int(v) for k, v in s.items()})
