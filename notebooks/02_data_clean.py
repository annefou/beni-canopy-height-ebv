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
# # 02 — Three layers on one grid, each saying what it is
#
# All layers are put on **HEALPix NESTED on the WGS84 ellipsoid, depth 11** (cells of ~3.2 km) with
# `healpix-connector` (GRID4EARTH). Depth 11 is the finest at which both 200 m BIOMASS pixels and 300 m Fire_cci
# pixels are at least 10 pixels across a cell, the rule `healpix-connector` enforces for area-weighted binning.
#
# **"Canopy height" is not one quantity.** The two height sources measure different things, quoted from their
# own documentation:
#
# | | BIOMASS L2A `FP_FH__L2A` | GEDI L2A V002 |
# |---|---|---|
# | Definition | "forest upper canopy height (H100 Standard)" (Forest Height ATBD v2.2.0, §3.5.1); "Top Canopy Height (TCH)" (Product Format Specification v3.4.0, §4.2) | "Relative height metrics at 1 % interval" (L2A data dictionary); RH100 = `elev_highestreturn − elev_lowestmode` (User Guide V2.1) |
# | Support | 200 m pixel, radar (P-band PolInSAR inversion) | ~25 m footprint, lidar waveform |
# | Quality | "a percentage bias value for each of the Forest Height image pixel" (PFS §4.2): **lower is better** | `quality_flag` = 1, `degrade_flag` = 0, `sensitivity` (max. canopy cover penetrated) |
#
# Both fit the CF standard name `canopy_height` ("the vertical distance above the surface" of "the outer surfaces
# of the vegetation", CF table v95), which is broad enough to hide the difference. So each variable below carries
# the CF name **and** its own definition, support and statistic; `03` treats relating one to the other as a model,
# not as an identity.

# %%
import json
import re
from pathlib import Path

import healpix_connector
import numpy as np
import pandas as pd
import rasterio
import xarray as xr
from healpix_connector.binning import bin_to_cells
from healpix_connector.conventions import ELLIPSOID, cell_size_m
from healpix_connector.dggs_zarr import cf_grid_mapping_attrs, dggs_attrs
from healpix_connector.sources.geotiff import read_window
from healpix_geo import nested

RAW = Path("../data/raw")
CLEAN = Path("../data/clean")
CLEAN.mkdir(parents=True, exist_ok=True)
BBOX = (-67.5, -15.5, -64.5, -12.5)
DEPTH = 11
EPS = 0.01  # ESA's adjustment factor in the inverse-bias weights (FH ATBD eq. 3.19)
print("healpix-connector", healpix_connector.__version__, f"| depth {DEPTH} = {cell_size_m(DEPTH)/1e3:.2f} km")

# %% [markdown]
# ## BIOMASS forest height, repeat passes combined the ESA way
#
# ESA's own L2b fusion averages passes pixel by pixel with weights 1/(ε + bias) (ATBD eq. 3.19). Here each pass is
# first binned to cells (mean height and mean bias per cell), then passes are combined per cell with weights
# pixel count / (ε + cell-mean bias): the cell-level analogue, stated as such.
#
# One product-level exclusion rule: a product whose **median bias is below 1 %** is set aside as suspect. A whole
# inversion with near-zero bias is implausible; in the ESA Frontiers `beni-pipeline` the two products with this
# pattern also lacked a height of ambiguity in their annotation and gave heights 20–26 m above overlapping
# passes. The annotation XML is searched for "ambiguity" and the count is recorded, so the rule can be checked.

# %%
def clipped_bbox(path: Path) -> tuple[float, float, float, float]:
    # Work-around: healpix-connector read_window misplaces pixels when the window extends beyond the file.
    with rasterio.open(path) as src:
        b = src.bounds
    return (max(BBOX[0], b.left), max(BBOX[1], b.bottom), min(BBOX[2], b.right), min(BBOX[3], b.top))


def read_masked(path: Path):
    w = read_window(str(path), clipped_bbox(path))
    w.values[w.values == -9999.0] = np.nan
    return w


items = json.loads((RAW / "biomass_fh" / "items.json").read_text())
per_pass, products = [], []
for it in items:
    fh_name, q_name = it["files"].get("enclosure_i_fh_tiff"), it["files"].get("enclosure_i_quality_tiff")
    if not (fh_name and q_name):
        continue
    xml = RAW / "biomass_fh" / it["files"].get("enclosure_xml", "")
    n_ambig = len(re.findall("ambiguity", xml.read_text(), re.I)) if xml.is_file() else None
    fh, q = read_masked(RAW / "biomass_fh" / fh_name), read_masked(RAW / "biomass_fh" / q_name)
    med_bias = float(np.nanmedian(q.values))
    rec = {"id": it["id"], "start": it["start"], "processor": it["processor"],
           "median_bias_pct": round(med_bias, 2), "ambiguity_mentions_in_annotation": n_ambig,
           "excluded": med_bias < 1.0}
    products.append(rec)
    if rec["excluded"]:
        continue
    assert fh.values.shape == q.values.shape, f"{it['id']}: height and quality grids differ"
    invalid = np.isnan(fh.values) | np.isnan(q.values)  # use only pixels valid in both layers
    fh.values[invalid] = np.nan
    q.values[invalid] = np.nan
    s_fh = bin_to_cells(fh.values, fh.lon, fh.lat, DEPTH, fh.res_deg)
    s_q = bin_to_cells(q.values, q.lon, q.lat, DEPTH, q.res_deg)
    assert np.array_equal(s_fh.cell_ids, s_q.cell_ids)
    full = s_fh.coverage > 0.9  # cells the swath covers fully
    per_pass.append(pd.DataFrame({"cell_id": s_fh.cell_ids[full], "fh": s_fh.mean[full], "bias": s_q.mean[full],
                                  "fh_within_std": s_fh.std[full], "n_px": s_fh.pixel_count[full],
                                  "start": it["start"]}))
products = pd.DataFrame(products)
print(products[["start", "median_bias_pct", "ambiguity_mentions_in_annotation", "excluded"]].to_string())

# %%
p = pd.concat(per_pass, ignore_index=True)
p["w"] = p["n_px"] / (EPS + p["bias"])
g = p.groupby("cell_id")
bio = pd.DataFrame({
    "fh": g.apply(lambda d: np.average(d["fh"], weights=d["w"]), include_groups=False),
    "bias": g.apply(lambda d: np.average(d["bias"], weights=d["w"]), include_groups=False),
    "fh_within_std": g.apply(lambda d: np.average(d["fh_within_std"], weights=d["w"]), include_groups=False),
    "fh_between_pass_std": g["fh"].std(ddof=0),
    "n_passes": g.size(),
})
print(f"{len(bio)} cells with BIOMASS forest height from {products['excluded'].eq(False).sum()} products")

# %% [markdown]
# ## GEDI footprints per cell
#
# Shots kept: `quality_flag` = 1, `degrade_flag` = 0, full-power beams, `sensitivity` ≥ 0.95. The GEDI user guide
# recommends power beams in dense forest and says that there "the user may benefit from selecting a higher
# threshold" than the 0.9 built into `quality_flag`; 0.95 is our choice and is recorded. Night shots
# (`solar_elevation` < 0) are kept and flagged; `03` checks that the result holds on night shots alone.
# Per cell: the median RH98 (robust to the occasional cloud or noise return), its spread, and the shot count.

# %%
gedi = pd.read_parquet(RAW / "gedi_l2a_beni.parquet")
keep = ((gedi["quality_flag"] == 1) & (gedi["degrade_flag"] == 0) & (gedi["sensitivity"] >= 0.95)
        & gedi["beam_type"].str.contains("full power", case=False))
gs = gedi[keep].copy()
gs["cell_id"] = nested.lonlat_to_healpix(gs["lon"].to_numpy(), gs["lat"].to_numpy(), np.uint8(DEPTH),
                                         ellipsoid=ELLIPSOID).astype("uint64")
gs["night"] = gs["solar_elevation"] < 0
q = lambda x, k: np.nanpercentile(x, k)
gg = gs.groupby("cell_id")
ged = pd.DataFrame({
    "rh98_median": gg["rh98"].median(),
    "rh98_iqr": gg["rh98"].agg(lambda x: q(x, 75) - q(x, 25)),
    "rh98_median_night": gs[gs["night"]].groupby("cell_id")["rh98"].median(),
    "n_shots": gg.size(), "n_shots_night": gg["night"].sum(),
    "first_shot": gg["time"].min(), "last_shot": gg["time"].max(),
})
print(f"{keep.sum()} of {len(gedi)} footprints kept, in {len(ged)} cells "
      f"({100*gs['night'].mean():.0f} % at night)")

# %% [markdown]
# ## Disturbance between the two: Fire_cci 2024
#
# GEDI shots span 2019–2025, BIOMASS passes are from 2026, and the Beni burned widely in 2024. Cells where fire
# changed the canopy between the two measurements cannot be used to relate them. Pixel codes (JD layer, from the
# Fire_cci Product User Guide, not the GeoTIFF): day of year = burned; 0 = not burned; −1 = not observed;
# −2 = not burnable. Burned share = burned / observed-and-burnable, as in `beni-fire-biomass-healpix`.

# %%
FIRE = ("https://dap.ceda.ac.uk/neodc/esacci/fire/data/burned_area/Sentinel3_SYN/pixel/v1.1/uncompressed/"
        "2024/{m:02d}/2024{m:02d}01-ESACCI-L3S_FIRE-BA-SYN-AREA_2-fv1.1-JD.tif")
burned = observed = unburnable = None
for m in range(1, 13):
    w = read_window(FIRE.format(m=m), BBOX)
    j = w.values
    if burned is None:
        burned, observed, unburnable = np.zeros(j.shape, bool), np.zeros(j.shape, bool), np.ones(j.shape, bool)
        lon, lat, res = w.lon, w.lat, w.res_deg
    burned |= j > 0; observed |= j >= 0; unburnable &= j == -2
fire = bin_to_cells(np.where(observed & ~unburnable, burned.astype(float), np.nan), lon, lat, DEPTH, res)
fire = pd.Series(fire.mean, index=pd.Index(fire.cell_ids, name="cell_id"), name="burned_share_2024")
print(f"{(fire > 0.05).mean()*100:.0f} % of cells had more than 5 % of their burnable area burned in 2024")

# %% [markdown]
# ## One self-describing store
#
# Written as GRID4EARTH DGGS Zarr (the `dggs` convention attributes are produced by `healpix-connector`, which
# matches the `healpix-convert` converter), under `measurements/canopy_height/11`. Every variable carries the CF
# attributes plus `definition` (quoted, with its source document), `support` and `statistic`.

# %%
cells = np.array(sorted(set(bio.index) | set(ged.index)), dtype="uint64")
T = pd.DataFrame(index=pd.Index(cells, name="cell_id")).join(bio).join(ged).join(fire)

FH_DEF = ("BIOMASS L2A forest height: 'forest upper canopy height (H100 Standard)' (BIOMASS Forest Height ATBD "
          "BIO-BPS-FH-ATBD-ARE-10343 v2.2.0, 2026-03-13, sec. 3.5.1); 'Top Canopy Height (TCH)' (BIOMASS Forest "
          "Height Products Format Specification BIO-BPS-FHPFD-ARE-010256 v3.4.0, sec. 4.2)")
BIAS_DEF = ("BIOMASS L2A forest height quality: 'a percentage bias value for each of the Forest Height image pixel, "
            "indicating the inversion performance' (Format Specification v3.4.0, sec. 4.2); computed as "
            "|k_hb - k_h| / k_h * 100 (ATBD eq. 3.22). Lower is better.")
RH_DEF = ("GEDI L2A rh: 'Relative height metrics at 1 % interval' (GEDI L2A data dictionary, product P003 v2); "
          "RH100 = elev_highestreturn - elev_lowestmode (GEDI L2 User Guide V2.1). rh98 is the height above the "
          "lowest mode at which 98 % of the returned waveform energy is reached.")
NO_STD = "No CF standard name exists for this quantity (CF standard name table v95)."


def var(col, attrs, dtype="float32"):
    return ("cells", T[col].to_numpy(dtype=dtype), {**attrs, "grid_mapping": "crs"})


ds = xr.Dataset(
    {
        "biomass_forest_height": var("fh", {
            "standard_name": "canopy_height", "units": "m", "long_name": "BIOMASS forest height (H100)",
            "definition": FH_DEF, "support": "200 m radar pixels, area-weighted mean over the cell",
            "statistic": "per pass: area-weighted cell mean; across passes: weighted mean, weights pixel_count/(0.01+bias)",
            "cell_methods": "area: mean", "ancillary_variables": "biomass_fh_bias biomass_n_passes",
            "source": "ESA BIOMASS L2A FP_FH__L2A via ESA MAAP (collection BiomassLevel2a)"}),
        "biomass_fh_bias": var("bias", {
            "units": "percent", "long_name": "BIOMASS forest-height inversion bias (quality index)",
            "definition": BIAS_DEF, "comment": NO_STD, "statistic": "same weighting as biomass_forest_height"}),
        "biomass_fh_within_cell_std": var("fh_within_std", {
            "units": "m", "long_name": "spread of BIOMASS forest height within the cell (weighted over passes)"}),
        "biomass_fh_between_pass_std": var("fh_between_pass_std", {
            "units": "m", "long_name": "spread of cell-mean BIOMASS forest height across passes"}),
        "biomass_n_passes": var("n_passes", {"standard_name": "number_of_observations", "units": "1",
                                             "long_name": "BIOMASS passes contributing to the cell"}),
        "gedi_rh98": var("rh98_median", {
            "standard_name": "canopy_height", "units": "m", "long_name": "GEDI relative height RH98, cell median",
            "definition": RH_DEF, "support": "~25 m lidar footprints inside the cell",
            "statistic": "median over kept footprints (quality_flag=1, degrade_flag=0, full-power beams, sensitivity>=0.95)",
            "cell_methods": "area: median", "ancillary_variables": "gedi_n_shots gedi_rh98_iqr",
            "source": "GEDI L2A V002 doi:10.5067/GEDI/GEDI02_A.002"}),
        "gedi_rh98_iqr": var("rh98_iqr", {"units": "m", "long_name": "interquartile range of GEDI RH98 in the cell"}),
        "gedi_rh98_night": var("rh98_median_night", {"units": "m", "standard_name": "canopy_height",
                                                     "long_name": "GEDI RH98, cell median of night shots only",
                                                     "definition": RH_DEF}),
        "gedi_n_shots": var("n_shots", {"standard_name": "number_of_observations", "units": "1",
                                        "long_name": "kept GEDI footprints in the cell"}),
        "burned_share_2024": var("burned_share_2024", {
            "standard_name": "burned_area_fraction", "units": "1", "cell_methods": "area: mean time: maximum",
            "long_name": "share of observed, burnable 300 m pixels burned at least once in 2024",
            "source": "ESA Fire_cci SYN burned area pixel v1.1 doi:10.5285/d441079fc77f49fabeb41330612b252f"}),
        "crs": ((), np.int8(0), cf_grid_mapping_attrs(DEPTH)),
    },
    coords={"cell_ids": ("cells", cells, {"standard_name": "healpix_index", "units": "1"})},
)
ds.attrs.update(dggs_attrs(DEPTH))
ds.attrs.update({"Conventions": "CF-1.8", "title": "Beni lowlands: BIOMASS and GEDI canopy heights on HEALPix",
                 "region_bbox_lonlat": list(BBOX), "producer": f"healpix-connector {healpix_connector.__version__}",
                 "biomass_products": products.to_json(orient="records")})
STORE = CLEAN / "beni_canopy_height.zarr"
ds.to_zarr(STORE, group=f"measurements/canopy_height/{DEPTH}", mode="w", zarr_format=3, consolidated=False)
products.to_csv(CLEAN / "biomass_products.csv", index=False)
ds
