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
# | ESA BIOMASS L2A forest height `FP_FH__L2A` (200 m), 2026 | Earth-observation estimate of canopy height | ESA MAAP, **credentials** |
# | NASA GEDI L2A V002 relative-height metrics (25 m footprints) | reference heights for calibration | NASA Earthdata, **credentials** |
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
# ## GEDI L2A V002 footprints (NASA Earthdata)
#
# Granules are streamed, not downloaded whole: from each beam we read only the footprint location, time, the
# relative-height metrics RH98 and RH100, and the quality fields named in the GEDI L2A user guide
# (`quality_flag`, `degrade_flag`, `sensitivity`, `solar_elevation`). Whether a beam is a full-power or a
# coverage beam is read from the beam group's own `description` attribute. Footprints outside the box are
# dropped. Output: `gedi_l2a_beni.parquet`, one row per footprint, plus the list of granules used.

# %%
import earthaccess
import h5py
import numpy as np
import pandas as pd

GEDI_PARQUET = RAW / "gedi_l2a_beni.parquet"
if not GEDI_PARQUET.exists():
    strategy = "environment" if os.environ.get("EARTHDATA_USERNAME") else "netrc"
    if not earthaccess.login(strategy=strategy):
        sys.exit("NASA Earthdata login failed: set EARTHDATA_USERNAME/EARTHDATA_PASSWORD or ~/.netrc.")
    granules = earthaccess.search_data(short_name="GEDI02_A", version="002", bounding_box=BBOX,
                                       temporal=(GEDI_START, GEDI_END))
    print(f"{len(granules)} GEDI L2A granules intersect the box")
    frames, used = [], []
    for g, fobj in zip(granules, earthaccess.open(granules)):
        with h5py.File(fobj, "r") as h5:
            for beam in [k for k in h5 if k.startswith("BEAM")]:
                b = h5[beam]
                lat, lon = b["lat_lowestmode"][:], b["lon_lowestmode"][:]
                inside = (lon >= BBOX[0]) & (lon <= BBOX[2]) & (lat >= BBOX[1]) & (lat <= BBOX[3])
                if not inside.any():
                    continue
                idx = np.flatnonzero(inside)
                rh = b["rh"][idx.min():idx.max() + 1][idx - idx.min()]
                frames.append(pd.DataFrame({
                    "shot_number": b["shot_number"][idx], "beam": beam,
                    "beam_type": b.attrs["description"].decode() if isinstance(b.attrs["description"], bytes)
                    else str(b.attrs["description"]),
                    "lon": lon[idx], "lat": lat[idx], "delta_time": b["delta_time"][idx],
                    "rh98": rh[:, 98], "rh100": rh[:, 100],
                    "quality_flag": b["quality_flag"][idx], "degrade_flag": b["degrade_flag"][idx],
                    "sensitivity": b["sensitivity"][idx], "solar_elevation": b["solar_elevation"][idx],
                }))
                used.append(g["meta"]["native-id"])
    gedi = pd.concat(frames, ignore_index=True)
    gedi["time"] = pd.Timestamp("2018-01-01", tz="UTC") + pd.to_timedelta(gedi["delta_time"], unit="s")
    gedi.to_parquet(GEDI_PARQUET)
    (RAW / "gedi_granules.json").write_text(json.dumps(sorted(set(used)), indent=1))
gedi = pd.read_parquet(GEDI_PARQUET)
print(f"{len(gedi)} GEDI footprints in the box, {gedi['time'].min():%Y-%m} .. {gedi['time'].max():%Y-%m}")

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
            "temporal": [GEDI_START, GEDI_END], "granules": "gedi_granules.json",
            "file": GEDI_PARQUET.name, "sha256": sha256(GEDI_PARQUET)},
        "fire_cci": {
            "name": "ESA Fire_cci SYN burned area pixel product v1.1, 2024",
            "doi": "10.5285/d441079fc77f49fabeb41330612b252f",
            "license": "ESA CCI data policy: free use, acknowledge ESA CCI and cite the DOI",
            "access": "window read in 02_data_clean (not stored)"},
    },
    "files": bio_files,
}
(RAW / "sources.json").write_text(json.dumps(SOURCES, indent=1))
print(len(bio_files) + 1, "files recorded")
