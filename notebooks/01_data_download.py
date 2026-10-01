# ---
# jupyter:
#   jupytext:
#     formats: py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.16.0
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # 01 — Data download
#
# Region: the Beni lowlands, Bolivia (bbox lon −67.5 to −64.5, lat −15.5 to −12.5), as in
# `beni-fire-biomass-healpix` and the ESA Frontiers `beni-pipeline`.
#
# | Dataset | Role | Access |
# |---|---|---|
# | ESA BIOMASS L2A forest height `FP_FH__L2A` (200 m), 2026 | ecosystem height, wall to wall | ESA MAAP, **credentials** |
# | NASA GEDI L2A V002 relative-height metrics (25 m footprints) | independent ecosystem height, for validation | NASA Earthdata, **credentials** |
# | NASA GEDI L2B V002 canopy cover, foliage height diversity, plant area volume density profile (25 m footprints) | ecosystem cover, structural complexity, relative vertical profile | NASA Earthdata, **credentials** |
# | ESA WorldCover 2021 v200 (10 m) | ecosystem focus group: tree cover | public; aggregated here to a 100 m tree-cover fraction |
# | ESA Fire_cci SYN burned area pixel v1.1, 2024 | mask of cells disturbed between GEDI and BIOMASS | streamed by window in `02` |
#
# **Credentials** come only from the environment, never from this repository, and are never printed
# (same convention as `beni-pipeline/00_get_biomass_fh.py`):
#
# | Service | Environment variables | Where to get them |
# |---|---|---|
# | ESA MAAP | `MAAP_OFFLINE_TOKEN` (or `MAAP_TOKEN_FILE`, a path to a file holding it), `MAAP_CLIENT_SECRET`, optional `MAAP_CLIENT_ID` (default `offline-token`) | token: <https://portal.maap.eo.esa.int/ini/services/auth/token/> (valid 90 days); client id/secret: ESA MAAP's BIOMASS data-access example |
# | NASA Earthdata | `EARTHDATA_USERNAME`, `EARTHDATA_PASSWORD` (or a `~/.netrc` entry for `urs.earthdata.nasa.gov`) | <https://urs.earthdata.nasa.gov> |
#
# In CI, store them as GitHub Actions secrets of the same names.
#
# Every file is recorded in `data/raw/sources.json` with its DOI, licence, access date and SHA-256. Raw rasters
# and footprints are not committed; they are re-downloadable.

# %%
import hashlib
import json
import os
import sys
from datetime import date
from pathlib import Path

import requests

RAW = Path("../data/raw")
BIO_DIR = RAW / "biomass_fh"
BIO_DIR.mkdir(parents=True, exist_ok=True)

BBOX = (-67.5, -15.5, -64.5, -12.5)  # lon_min, lat_min, lon_max, lat_max
MAAP_CATALOG = "https://catalog.maap.eo.esa.int/catalogue"
MAAP_IAM = "https://iam.maap.eo.esa.int/realms/esa-maap/protocol/openid-connect/token"
GEDI_START, GEDI_END = "2019-04-04", "2025-07-10"  # the whole GEDI L2A V002 record (CMR temporal extent)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# %% [markdown]
# ## BIOMASS L2A forest height (ESA MAAP)
#
# The catalogue query is public; the files need a MAAP token. Per product we keep the forest-height raster, its
# quality raster and the annotation XML, and record each catalogue item (identifier, acquisition period,
# footprint, processor version, collection DOI) in `biomass_fh/items.json`.

# %%
r = requests.get(f"{MAAP_CATALOG}/collections/BiomassLevel2a/items",
                 params={"bbox": ",".join(map(str, BBOX)), "limit": 200,
                         "filter": "product:type='FP_FH__L2A'"},
                 headers={"Accept": "application/geo+json"}, timeout=120)
r.raise_for_status()
items = r.json()["features"]
print(f"{len(items)} BIOMASS L2A forest-height products over the box")


def maap_access_token() -> str:
    offline = os.environ.get("MAAP_OFFLINE_TOKEN")
    if not offline and os.environ.get("MAAP_TOKEN_FILE"):
        offline = Path(os.environ["MAAP_TOKEN_FILE"]).read_text()
    secret = os.environ.get("MAAP_CLIENT_SECRET", "")
    if not offline or not secret:
        sys.exit("Set MAAP_OFFLINE_TOKEN (or MAAP_TOKEN_FILE) and MAAP_CLIENT_SECRET; see the table above.")
    r = requests.post(MAAP_IAM, data={"client_id": os.environ.get("MAAP_CLIENT_ID", "offline-token"),
                                      "client_secret": secret, "grant_type": "refresh_token",
                                      "refresh_token": offline.strip().replace("\n", ""),
                                      "scope": "offline_access openid"}, timeout=60)
    if r.status_code != 200:
        sys.exit(f"MAAP token exchange failed: HTTP {r.status_code} {r.json().get('error_description', '')}")
    return r.json()["access_token"]


session = requests.Session()
session.headers["Authorization"] = f"Bearer {maap_access_token()}"
bio_records, bio_files = [], []
for f in items:
    p = f["properties"]
    rec = {"id": f["id"], "start": p.get("start_datetime"), "end": p.get("end_datetime"),
           "orbit_state": p.get("sat:orbit_state"), "mission_phase": p.get("eofeos:mission_phase"),
           "processor": p.get("processing:software"), "collection_doi": p.get("sci:doi"),
           "geometry": f["geometry"], "files": {}}
    for key in ("enclosure_i_fh_tiff", "enclosure_i_quality_tiff", "enclosure_xml"):
        a = f["assets"].get(key)
        if not a:
            continue
        dest = BIO_DIR / Path(a["href"]).name
        if not dest.exists():
            resp = session.get(a["href"], timeout=600)
            if resp.status_code != 200:
                print(f"  {key} {f['id'][:40]}: HTTP {resp.status_code}")
                continue
            dest.write_bytes(resp.content)
        rec["files"][key] = dest.name
        bio_files.append({"file": f"biomass_fh/{dest.name}", "url": a["href"], "sha256": sha256(dest),
                          "dataset": "biomass_l2a_fh"})
    bio_records.append(rec)
(BIO_DIR / "items.json").write_text(json.dumps(bio_records, indent=1))
print(f"{len(bio_files)} BIOMASS files; processors: "
      f"{sorted({json.dumps(r['processor']) for r in bio_records})}")

# %% [markdown]
# ## GEDI L2A and L2B V002 footprints (NASA Earthdata)
#
# Granules are streamed, not downloaded whole. Only the fields used are read, by name, wherever they sit inside
# the beam group (the data dictionaries list them without their group paths):
#
# - **L2A:** location, time, the relative-height metrics RH98 and RH100 (`rh`, "Relative height metrics at 1 %
#   interval"), `quality_flag`, `degrade_flag`, `sensitivity`, `solar_elevation`.
# - **L2B:** `cover` ("Total canopy cover, defined as the percent of the ground covered by the vertical projection
#   of canopy material"; stored as a fraction 0–1), `fhd_normal` ("Foliage height diversity index"), `pavd_z`
#   ("Vertical Plant Area Volume Density profile with a vertical step size of dZ", m² m⁻³), `dz`,
#   `l2b_quality_flag`, `algorithmrun_flag`, plus the same location, time and quality fields.
#
# Whether a beam is a full-power or a coverage beam is read from the beam group's own `description` attribute.
# Footprints outside the box are dropped. Outputs: one parquet file per product, one row per footprint, plus the
# list of granules used.

# %%
import earthaccess
import h5py
import numpy as np
import pandas as pd


def find(group: h5py.Group, name: str) -> h5py.Dataset:
    """Dataset ``name`` directly in ``group`` or in one of its subgroups."""
    if name in group and isinstance(group[name], h5py.Dataset):
        return group[name]
    hits = []
    group.visititems(lambda path, obj: hits.append(obj) if isinstance(obj, h5py.Dataset)
                     and path.split("/")[-1] == name else None)
    if not hits:
        raise KeyError(f"{name} not in {group.name}")
    return hits[0]


def beam_type(b: h5py.Group) -> str:
    d = b.attrs.get("description", b"")
    return d.decode() if isinstance(d, bytes) else str(d)


def read_l2a(b: h5py.Group, idx: np.ndarray) -> dict:
    rh = find(b, "rh")[idx.min():idx.max() + 1][idx - idx.min()]
    return {"rh98": rh[:, 98], "rh100": rh[:, 100], "quality_flag": find(b, "quality_flag")[idx]}


def read_l2b(b: h5py.Group, idx: np.ndarray) -> dict:
    pavd = find(b, "pavd_z")[idx.min():idx.max() + 1][idx - idx.min()]
    cols = {"cover": find(b, "cover")[idx], "fhd_normal": find(b, "fhd_normal")[idx],
            "l2b_quality_flag": find(b, "l2b_quality_flag")[idx], "algorithmrun_flag": find(b, "algorithmrun_flag")[idx],
            "dz": float(np.ravel(find(b, "dz")[()])[0])}
    cols.update({f"pavd_{k:02d}": pavd[:, k] for k in range(pavd.shape[1])})
    return cols


def stream(short_name: str, reader) -> tuple[pd.DataFrame, list[str]]:
    granules = earthaccess.search_data(short_name=short_name, version="002", bounding_box=BBOX,
                                       temporal=(GEDI_START, GEDI_END))
    print(f"{len(granules)} {short_name} granules intersect the box")
    frames, used = [], []
    for g, fobj in zip(granules, earthaccess.open(granules)):
        with h5py.File(fobj, "r") as h5:
            for beam in [k for k in h5 if k.startswith("BEAM")]:
                b = h5[beam]
                lat, lon = find(b, "lat_lowestmode")[:], find(b, "lon_lowestmode")[:]
                inside = (lon >= BBOX[0]) & (lon <= BBOX[2]) & (lat >= BBOX[1]) & (lat <= BBOX[3])
                if not inside.any():
                    continue
                idx = np.flatnonzero(inside)
                frames.append(pd.DataFrame({
                    "shot_number": find(b, "shot_number")[idx], "beam": beam, "beam_type": beam_type(b),
                    "lon": lon[idx], "lat": lat[idx], "delta_time": find(b, "delta_time")[idx],
                    "degrade_flag": find(b, "degrade_flag")[idx], "sensitivity": find(b, "sensitivity")[idx],
                    "solar_elevation": find(b, "solar_elevation")[idx], **reader(b, idx)}))
                used.append(g["meta"]["native-id"])
    df = pd.concat(frames, ignore_index=True)
    df["time"] = pd.Timestamp("2018-01-01", tz="UTC") + pd.to_timedelta(df["delta_time"], unit="s")
    return df, sorted(set(used))


GEDI = {"GEDI02_A": (RAW / "gedi_l2a_beni.parquet", read_l2a), "GEDI02_B": (RAW / "gedi_l2b_beni.parquet", read_l2b)}
if not all(path.exists() for path, _ in GEDI.values()):
    strategy = "environment" if os.environ.get("EARTHDATA_USERNAME") else "netrc"
    if not earthaccess.login(strategy=strategy):
        sys.exit("NASA Earthdata login failed: set EARTHDATA_USERNAME/EARTHDATA_PASSWORD or ~/.netrc.")
gedi_granules = {}
for short_name, (path, reader) in GEDI.items():
    granule_list = RAW / f"{short_name.lower()}_granules.json"
    if not path.exists():
        df, used = stream(short_name, reader)
        df.to_parquet(path)
        granule_list.write_text(json.dumps(used, indent=1))
    df = pd.read_parquet(path)
    gedi_granules[short_name] = granule_list.name
    print(f"{short_name}: {len(df)} footprints in the box, {df['time'].min():%Y-%m} .. {df['time'].max():%Y-%m}")

# %% [markdown]
# ## Ecosystem focus group: tree cover from ESA WorldCover 2021
#
# The EBV is defined per ecosystem focus group; here the group is forest, taken as WorldCover class 10,
# "Tree cover" (legend stored in the files themselves). The four 10 m tiles covering the box are read in strips
# and reduced to the share of tree-cover pixels per 100 m block (10 × 10 pixels), written as one NetCDF file.
# `02` uses it per cell and per GEDI footprint.

# %%
import rasterio
import xarray as xr
from rasterio.windows import from_bounds

WC_URL = "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_{t}_Map.tif"
WC_TILES = ["S15W069", "S15W066", "S18W069", "S18W066"]
TREE, AGG = 10, 10  # WorldCover class "Tree cover"; 10 x 10 pixels of 10 m = 100 m
WC_OUT = RAW / "worldcover2021_treecover_fraction_100m.nc"

if not WC_OUT.exists():
    res = 1 / 12000  # WorldCover pixel size in degrees
    nx, ny = round((BBOX[2] - BBOX[0]) / res) // AGG, round((BBOX[3] - BBOX[1]) / res) // AGG
    frac = np.full((ny, nx), np.nan, dtype="float32")
    for tile in WC_TILES:
        with rasterio.open("/vsicurl/" + WC_URL.format(t=tile)) as src:
            b = src.bounds
            box = (max(BBOX[0], b.left), max(BBOX[1], b.bottom), min(BBOX[2], b.right), min(BBOX[3], b.top))
            if box[0] >= box[2] or box[1] >= box[3]:
                continue
            win = from_bounds(*box, src.transform).round_offsets().round_lengths()
            col0 = round((box[0] - BBOX[0]) / res) // AGG
            row0 = round((BBOX[3] - box[3]) / res) // AGG
            for r in range(0, int(win.height), 1200):  # strips of 1200 rows (12 km)
                h = min(1200, int(win.height) - r)
                a = src.read(1, window=rasterio.windows.Window(win.col_off, win.row_off + r, win.width, h))
                a = a[: h // AGG * AGG, : int(win.width) // AGG * AGG]
                tree = (a == TREE).reshape(a.shape[0] // AGG, AGG, a.shape[1] // AGG, AGG).mean(axis=(1, 3))
                valid = (a != 0).reshape(tree.shape[0], AGG, tree.shape[1], AGG).any(axis=(1, 3))
                rr = row0 + r // AGG
                frac[rr:rr + tree.shape[0], col0:col0 + tree.shape[1]] = np.where(valid, tree, np.nan)
    lon = BBOX[0] + (np.arange(nx) + 0.5) * res * AGG
    lat = BBOX[3] - (np.arange(ny) + 0.5) * res * AGG
    xr.Dataset({"tree_cover_fraction": (("lat", "lon"), frac, {
        "units": "1", "long_name": "share of 10 m pixels classified 'Tree cover' (class 10) in each 100 m block",
        "source": "ESA WorldCover 10 m 2021 v200, doi:10.5281/zenodo.7254221"})},
        coords={"lat": ("lat", lat, {"units": "degrees_north"}), "lon": ("lon", lon, {"units": "degrees_east"})},
        attrs={"tiles": " ".join(WC_TILES), "aggregation": f"{AGG} x {AGG} pixels"}).to_netcdf(WC_OUT)
wc = xr.open_dataset(WC_OUT)
print(f"tree-cover fraction grid {dict(wc.sizes)}, mean {float(wc.tree_cover_fraction.mean()):.2f}")

# %%
SOURCES = {
    "accessed_on": date.today().isoformat(),
    "region_bbox_lonlat": list(BBOX),
    "datasets": {
        "biomass_l2a_fh": {
            "name": "ESA BIOMASS Level-2A forest height (FP_FH__L2A)",
            "doi": sorted({r["collection_doi"] for r in bio_records if r["collection_doi"]}),
            "license": "ESA/NASA MAAP open data policy: free and open; free MAAP registration needed",
            "catalogue": f"{MAAP_CATALOG}/collections/BiomassLevel2a"},
        "gedi_l2a": {
            "name": "GEDI L2A Elevation and Height Metrics Data Global Footprint Level V002",
            "doi": "10.5067/GEDI/GEDI02_A.002", "license": "NASA Earthdata: no restrictions on reuse",
            "temporal": [GEDI_START, GEDI_END], "granules": gedi_granules["GEDI02_A"],
            "file": GEDI["GEDI02_A"][0].name, "sha256": sha256(GEDI["GEDI02_A"][0])},
        "gedi_l2b": {
            "name": "GEDI L2B Canopy Cover and Vertical Profile Metrics Data Global Footprint Level V002",
            "doi": "10.5067/GEDI/GEDI02_B.002", "license": "NASA Earthdata: no restrictions on reuse",
            "temporal": [GEDI_START, GEDI_END], "granules": gedi_granules["GEDI02_B"],
            "file": GEDI["GEDI02_B"][0].name, "sha256": sha256(GEDI["GEDI02_B"][0])},
        "worldcover": {
            "name": "ESA WorldCover 10 m 2021 v200", "doi": "10.5281/zenodo.7254221", "license": "CC-BY-4.0",
            "tiles": [WC_URL.format(t=x) for x in WC_TILES],
            "file": WC_OUT.name, "sha256": sha256(WC_OUT), "derived": "tree-cover fraction per 100 m block"},
        "fire_cci": {
            "name": "ESA Fire_cci SYN burned area pixel product v1.1, 2024",
            "doi": "10.5285/d441079fc77f49fabeb41330612b252f",
            "license": "ESA CCI data policy: free use, acknowledge ESA CCI and cite the DOI",
            "access": "window read in 02_data_clean (not stored)"},
    },
    "files": bio_files,
}
(RAW / "sources.json").write_text(json.dumps(SOURCES, indent=1))
print(len(bio_files) + 3, "files recorded")
