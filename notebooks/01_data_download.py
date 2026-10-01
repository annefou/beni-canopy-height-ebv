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
# | NASA GEDI L2A V003 relative-height metrics (25 m footprints) | independent ecosystem height, for validation | NASA Earthdata, **credentials** |
# | NASA GEDI L2B V003 canopy cover, foliage height diversity, plant area volume density profile (25 m footprints) | ecosystem cover, structural complexity, relative vertical profile | NASA Earthdata, **credentials** |
# | ESA WorldCover 2021 v200 (10 m) | ecosystem focus group: tree cover | public; aggregated here to a 100 m tree-cover fraction |
# | ESA Fire_cci SYN burned area pixel v1.1, 2024 | mask of cells disturbed between GEDI and BIOMASS | streamed by window in `02` |
#
# **Credentials** come only from the environment, never from this repository, and are never printed
# (same convention as `beni-pipeline/00_get_biomass_fh.py`):
#
# | Service | Environment variables | Where to get them |
# |---|---|---|
# | ESA MAAP | `MAAP_OFFLINE_TOKEN`, or `MAAP_TOKEN_FILE` (a path to a file holding it) | <https://portal.maap.eo.esa.int/ini/services/auth/token/> (valid 90 days) |
# | NASA Earthdata | `EARTHDATA_USERNAME`, `EARTHDATA_PASSWORD` (or a `~/.netrc` entry for `urs.earthdata.nasa.gov`) | <https://urs.earthdata.nasa.gov> |
#
# In CI, store them as GitHub Actions secrets of the same names. The MAAP token exchange also needs a client id and
# secret; these are public, the same for every user, and published in ESA MAAP's token-access example
# (<https://docs.maap-project.org/en/latest/science/ESA_CCI/ESA_CCI_V5_Token_Access.html>), so they are the defaults
# below (`MAAP_CLIENT_ID` / `MAAP_CLIENT_SECRET` override them).
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
# Public client of ESA MAAP's token-access example (not a personal credential).
MAAP_PUBLIC_CLIENT = ("offline-token", "p1eL7uonXs6MDxtGbgKdPVRAmnGxHpVE")
GEDI_START, GEDI_END = "2019-04-04", date.today().isoformat()  # the whole GEDI V003 record (CMR: 2019-04-04 onwards)


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
    if not offline:
        sys.exit("Set MAAP_OFFLINE_TOKEN (or MAAP_TOKEN_FILE); see the table above.")
    secret = os.environ.get("MAAP_CLIENT_SECRET", MAAP_PUBLIC_CLIENT[1])
    r = requests.post(MAAP_IAM, data={"client_id": os.environ.get("MAAP_CLIENT_ID", MAAP_PUBLIC_CLIENT[0]),
                                      "client_secret": secret, "grant_type": "refresh_token",
                                      "refresh_token": offline.strip().replace("\n", ""),
                                      "scope": "offline_access openid"}, timeout=60)
    if r.status_code != 200:
        sys.exit(f"MAAP token exchange failed: HTTP {r.status_code} {r.json().get('error_description', '')}")
    return r.json()["access_token"]


session = requests.Session()
missing = [a["href"] for f in items for k, a in f["assets"].items()
           if k in ("enclosure_i_fh_tiff", "enclosure_i_quality_tiff", "enclosure_xml")
           and not (BIO_DIR / Path(a["href"]).name).exists()]
if missing:  # a token is only needed when something is left to download
    session.headers["Authorization"] = f"Bearer {maap_access_token()}"
print(f"{len(missing)} BIOMASS files to download")
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
# ## GEDI L2A and L2B V003 footprints (NASA Earthdata, subset by NASA Harmony)
#
# Reading whole GEDI granules to keep the few footprints inside the box is slow (about 70 s per granule, and
# the box crosses about 700 granules per product). NASA's **Harmony** service cuts each granule to the box on
# NASA's side (its trajectory subsetter); for these collections it cannot also drop variables, so each subset
# file is read for the fields below and then deleted. Jobs are one month each, and a finished month is recorded,
# so a rerun resumes.
#
# Harmony serves **Version 3** of GEDI L2A/L2B. Field names and flags differ from V002 and are taken from the V3
# data dictionaries and the GEDI L2 User Guide V3:
#
# - **L2A:** location, time, `rh` ("Relative height metrics at 1 % interval"; RH98 and RH100 kept),
#   `l2a_quality_flag_rel3`, `degrade_flag`, `sensitivity`, `solar_elevation`.
# - **L2B:** `cover` ("Total canopy cover, defined as the percent of the ground covered by the vertical projection
#   of canopy material", range 0–1, so a fraction), `fhd_normal` ("Foliage height diversity index"), `pavd_z`
#   ("Vertical Plant Area Volume Density profile from ground (z=0) to canopy top with a vertical step size of
#   dZ", m² m⁻³), `dz`, `l2b_quality_flag_rel3`, `l2_algrunflag`, plus the same location, time and quality
#   fields.
#
# Fields are found by name inside each beam group (root first). Whether a beam is a full-power or a coverage beam
# is read from the beam group's `description` attribute. Outputs: one parquet file per product, one row per
# footprint, plus the list of granules used.

# %%
import shutil

import h5py
import numpy as np
import pandas as pd
from harmony import BBox, Client, Collection, Request

GEDI_COLLECTIONS = {"GEDI02_A": "C3974616071-LPCLOUD", "GEDI02_B": "C3974616135-LPCLOUD"}  # V003 on LP DAAC
GEDI_DOI = {"GEDI02_A": "10.5067/GEDI/GEDI02_A.003", "GEDI02_B": "10.5067/GEDI/GEDI02_B.003"}


def find(group: h5py.Group, name: str) -> h5py.Dataset:
    """Dataset ``name`` directly in ``group``, else in one of its subgroups."""
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


def read_l2a(b: h5py.Group) -> dict:
    rh = find(b, "rh")[:]
    return {"rh98": rh[:, 98], "rh100": rh[:, 100], "l2a_quality_flag_rel3": find(b, "l2a_quality_flag_rel3")[:]}


def read_l2b(b: h5py.Group) -> dict:
    pavd = find(b, "pavd_z")[:]
    cols = {"cover": find(b, "cover")[:], "fhd_normal": find(b, "fhd_normal")[:],
            "l2b_quality_flag_rel3": find(b, "l2b_quality_flag_rel3")[:], "l2_algrunflag": find(b, "l2_algrunflag")[:],
            "dz": float(np.ravel(find(b, "dz")[()])[0])}
    cols.update({f"pavd_{k:02d}": pavd[:, k] for k in range(pavd.shape[1])})
    return cols


def footprints(path: Path, reader) -> pd.DataFrame:
    frames = []
    with h5py.File(path, "r") as h5:
        for beam in [k for k in h5 if k.startswith("BEAM")]:
            b = h5[beam]
            lat, lon = find(b, "lat_lowestmode")[:], find(b, "lon_lowestmode")[:]
            if lat.size == 0:
                continue
            frames.append(pd.DataFrame({
                "shot_number": find(b, "shot_number")[:], "beam": beam, "beam_type": beam_type(b),
                "lon": lon, "lat": lat, "delta_time": find(b, "delta_time")[:],
                "degrade_flag": find(b, "degrade_flag")[:], "sensitivity": find(b, "sensitivity")[:],
                "solar_elevation": find(b, "solar_elevation")[:], **reader(b)}))
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if len(df):  # the subsetter keeps whole along-track chunks: keep the box only
        df = df[(df.lon >= BBOX[0]) & (df.lon <= BBOX[2]) & (df.lat >= BBOX[1]) & (df.lat <= BBOX[3])]
    return df


def harmony_product(client: Client, short_name: str, reader) -> tuple[pd.DataFrame, list[str]]:
    """Submit one Harmony job per month (processed in parallel on NASA's side), then fetch, read and delete each."""
    parts, tmp = RAW / "gedi_parts" / short_name, RAW / "gedi_tmp" / short_name
    parts.mkdir(parents=True, exist_ok=True)
    tmp.mkdir(parents=True, exist_ok=True)
    jobs_file = parts / "harmony_jobs.json"
    jobs = json.loads(jobs_file.read_text()) if jobs_file.exists() else {}
    months = pd.date_range(GEDI_START, GEDI_END, freq="MS").union([pd.Timestamp(GEDI_START), pd.Timestamp(GEDI_END)])
    for start, stop in zip(months[:-1], months[1:]):
        key = f"{start:%Y-%m}"
        if key in jobs or (parts / f"{key}.done").exists():
            continue
        req = Request(collection=Collection(id=GEDI_COLLECTIONS[short_name]), spatial=BBox(*BBOX),
                      temporal={"start": start.to_pydatetime(), "stop": stop.to_pydatetime()})
        try:
            jobs[key] = client.submit(req)
        except Exception as e:  # e.g. a month inside GEDI's 2023-2024 gap: nothing to process
            (parts / f"{key}.done").write_text(f"not submitted: {str(e)[:200]}\n")
        jobs_file.write_text(json.dumps(jobs, indent=1))
    print(f"{short_name}: {len(jobs)} Harmony jobs")
    for key, job in sorted(jobs.items()):
        done = parts / f"{key}.done"
        if done.exists():
            continue
        client.wait_for_processing(job, show_progress=False)
        n = 0
        for fut in client.download_all(job, directory=str(tmp), overwrite=True):
            path = Path(fut.result())
            footprints(path, reader).to_parquet(parts / f"{path.stem}.parquet")
            path.unlink()
            n += 1
        done.write_text(f"{n} granules, Harmony job {job}\n")
        print(f"  {short_name} {key}: {n} granules")
    shutil.rmtree(tmp, ignore_errors=True)
    files = sorted(parts.glob("*.parquet"))
    dfs = [pd.read_parquet(f) for f in files]
    used = [f.stem for f, d in zip(files, dfs) if len(d)]
    df = pd.concat([d for d in dfs if len(d)], ignore_index=True)
    df["time"] = pd.Timestamp("2018-01-01", tz="UTC") + pd.to_timedelta(df["delta_time"], unit="s")
    return df, used


GEDI = {"GEDI02_A": (RAW / "gedi_l2a_beni.parquet", read_l2a), "GEDI02_B": (RAW / "gedi_l2b_beni.parquet", read_l2b)}
client = Client()  # NASA Earthdata login from EARTHDATA_USERNAME/EARTHDATA_PASSWORD or ~/.netrc
gedi_granules = {}
for short_name, (path, reader) in GEDI.items():
    granule_list = RAW / f"{short_name.lower()}_granules.json"
    if not path.exists():
        df, used = harmony_product(client, short_name, reader)
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
            "name": "GEDI L2A Elevation and Height Metrics Data Global Footprint Level V003",
            "doi": GEDI_DOI["GEDI02_A"], "access": "NASA Harmony trajectory subsetter (bounding box)", "license": "NASA Earthdata: no restrictions on reuse",
            "temporal": [GEDI_START, GEDI_END], "granules": gedi_granules["GEDI02_A"],
            "file": GEDI["GEDI02_A"][0].name, "sha256": sha256(GEDI["GEDI02_A"][0])},
        "gedi_l2b": {
            "name": "GEDI L2B Canopy Cover and Vertical Profile Metrics Data Global Footprint Level V003",
            "doi": GEDI_DOI["GEDI02_B"], "access": "NASA Harmony trajectory subsetter (bounding box)", "license": "NASA Earthdata: no restrictions on reuse",
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
