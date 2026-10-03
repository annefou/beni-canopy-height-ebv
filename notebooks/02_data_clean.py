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
# # 02 — All layers on one grid, each saying what it is
#
# > **In the published Jupyter Book this step is shown without outputs.** It needs ESA MAAP and NASA
# > Earthdata credentials and hours of downloads. Its product, the per-cell store
# > `data/clean/beni_canopy_height.zarr`, is committed, so `03` and `04` run from it.
#
# **What we are producing.** A dataset for the GEO BON EBV *Ecosystem Vertical Profile* (class Ecosystem
# Structure). EuropaBON D4.1 (2022) specifies it as the "Percentage of the relative vertical distribution of volume
# and biomass in the ecosystem focus group". Valbuena et al. 2020 (Trends Ecol. Evol., doi:10.1016/j.tree.2020.03.006)
# summarise vertical structure from 3D sources by three ecosystem morphological traits: *ecosystem height*
# ("Average height of the highest ecosystem structural elements … top of canopy height in forests"), *ecosystem
# cover* ("Percentage of a fixed area covered by the vertical projection" of the structural elements) and
# *structural complexity* ("Variability in height and/or cover … Standard deviation and coefficient of variation
# are common measures"). This step prepares all four: the three traits and the relative profile itself.
#
# All layers are put on **HEALPix NESTED on the WGS84 ellipsoid, depth 11** (cells of ~3.2 km) with
# `healpix-connector` (GRID4EARTH). Depth 11 is the finest at which both 200 m BIOMASS pixels and 300 m Fire_cci
# pixels are at least 10 pixels across a cell, the rule `healpix-connector` enforces for area-weighted binning.
#
# **"Canopy height" is not one quantity.** The two height sources measure different things, quoted from their
# own documentation:
#
# | | BIOMASS L2A `FP_FH__L2A` | GEDI L2A V003 |
# |---|---|---|
# | Definition | "forest upper canopy height (H100 Standard)" (Forest Height ATBD v2.2.0, §3.5.1); "Top Canopy Height (TCH)" (Product Format Specification v3.4.0, §4.2) | "Relative height metrics at 1 % interval" (L2A V3 data dictionary); RH100 = `elev_highestreturn − elev_lowestmode` (L2 User Guide V2.1) |
# | Support | 200 m pixel, radar (P-band PolInSAR inversion) | ~25 m footprint, lidar waveform |
# | Quality | "a percentage bias value for each of the Forest Height image pixel" (PFS §4.2): **lower is better** | `l2a_quality_flag_rel3` = 1 (L2 User Guide V3: includes `sensitivity` > 0.98 in tropical forest), `degrade_flag` = 0 |
#
# Both fit the CF standard name `canopy_height` ("the vertical distance above the surface" of "the outer surfaces
# of the vegetation", CF table v95), which is broad enough to hide the difference. So each variable below carries
# the CF name **and** its own definition, support and statistic; `03` treats relating one to the other as a model,
# not as an identity.

# %%
import json

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
# ## Ecosystem focus group: forest
#
# The EBV is defined per ecosystem focus group. Here the group is forest: ESA WorldCover 2021 class 10, "Tree
# cover". A cell belongs to the group when at least half of it is tree cover. A GEDI footprint, and a BIOMASS
# pixel, belongs to it when the 100 m block it falls in is at least half tree cover, so that both height sources
# describe the forest in the cell, not the cell. The thresholds are ours and are recorded.

# %%
FOREST_MIN = 0.5
wc = xr.open_dataset(RAW / "worldcover2021_treecover_fraction_100m.nc")
wres = float(abs(wc.lon[1] - wc.lon[0]))
tc = bin_to_cells(wc.tree_cover_fraction.values.astype("float64"), wc.lon.values, wc.lat.values, DEPTH, wres)
tree = pd.Series(tc.mean, index=pd.Index(tc.cell_ids, name="cell_id"), name="tree_cover_fraction")


NONFOREST_MAX_M = 20.0  # product exclusion: median height on non-forest pixels above this
MIN_FOREST_PX = 25  # BIOMASS pixels are posted every ~90 m: 25 pixels is ~0.2 km2 of forest in a ~10 km2 cell


def in_forest(lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    f = wc.tree_cover_fraction.sel(lon=xr.DataArray(lon), lat=xr.DataArray(lat), method="nearest").values
    return f >= FOREST_MIN


def tree_fraction_at(lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    """WorldCover tree-cover fraction at the centre of every pixel of a regular (lat, lon) grid."""
    return wc.tree_cover_fraction.sel(lon=xr.DataArray(lon, dims="x"), lat=xr.DataArray(lat, dims="y"),
                                      method="nearest").values


print(f"{(tree >= FOREST_MIN).mean()*100:.0f} % of cells are at least {FOREST_MIN:.0%} tree cover")

# %% [markdown]
# ## BIOMASS forest height, repeat passes combined the ESA way
#
# ESA's own L2b fusion averages passes pixel by pixel with weights 1/(ε + bias) (ATBD eq. 3.19). Here each pass is
# first binned to cells (mean height and mean bias per cell), then passes are combined per cell with weights
# pixel count / (ε + cell-mean bias): the cell-level analogue, stated as such.
#
# Only forest pixels enter the height (focus group above); whether a cell is fully covered by the swath is judged
# on all valid pixels, and a cell needs at least `MIN_FOREST_PX` forest pixels in a pass.
#
# One product-level exclusion rule, based on what must hold physically: a product is excluded when its **median
# height on clearly non-forest pixels** (WorldCover tree cover < 20 %, mostly grassland and savanna) is above
# `NONFOREST_MAX_M` = 20 m, i.e. when it reports tall canopy where there is none. The 20 m limit is our choice;
# for these products any limit between about 10 m and 29 m gives the same decisions.
#
# An earlier rule ("median bias below 1 %", used in the ESA Frontiers `beni-pipeline`) is shown for comparison in
# `excluded_by_bias_rule`. It removed two passes of 2026-07-25: one is clearly failed (about 30 m on forest and on
# grassland alike), the other is plausible (about 20 m on forest, 8 m on grassland). The BIOMASS bias index
# itself is kept and used to weight passes, as ESA does.

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
    fh, q = read_masked(RAW / "biomass_fh" / fh_name), read_masked(RAW / "biomass_fh" / q_name)
    tf = tree_fraction_at(fh.lon, fh.lat)
    med_bias = float(np.nanmedian(q.values))
    rec = {"id": it["id"], "start": it["start"], "processor": it["processor"],
           "median_bias_pct": round(med_bias, 2),
           "median_height_forest_px_m": round(float(np.nanmedian(fh.values[tf >= FOREST_MIN])), 1),
           "median_height_nonforest_px_m": round(float(np.nanmedian(fh.values[tf < 0.2])), 1),
           "excluded_by_bias_rule": med_bias < 1.0}
    rec["excluded"] = rec["median_height_nonforest_px_m"] > NONFOREST_MAX_M
    products.append(rec)
    if rec["excluded"]:
        continue
    assert fh.values.shape == q.values.shape, f"{it['id']}: height and quality grids differ"
    invalid = np.isnan(fh.values) | np.isnan(q.values)  # use only pixels valid in both layers
    fh.values[invalid] = np.nan
    q.values[invalid] = np.nan
    s_all = bin_to_cells(fh.values, fh.lon, fh.lat, DEPTH, fh.res_deg)  # swath coverage, all valid pixels
    nonforest = tf < FOREST_MIN
    fh.values[nonforest] = np.nan
    q.values[nonforest] = np.nan
    s_fh = bin_to_cells(fh.values, fh.lon, fh.lat, DEPTH, fh.res_deg)
    s_q = bin_to_cells(q.values, q.lon, q.lat, DEPTH, q.res_deg)
    assert np.array_equal(s_fh.cell_ids, s_q.cell_ids)
    cov = pd.Series(s_all.coverage, index=s_all.cell_ids).reindex(s_fh.cell_ids).to_numpy()
    full = (cov > 0.9) & (s_fh.pixel_count >= MIN_FOREST_PX)  # swath covers the cell; enough forest pixels
    per_pass.append(pd.DataFrame({"cell_id": s_fh.cell_ids[full], "fh": s_fh.mean[full], "bias": s_q.mean[full],
                                  "fh_within_std": s_fh.std[full], "n_px": s_fh.pixel_count[full],
                                  "start": it["start"]}))
products = pd.DataFrame(products)
print(products[["start", "median_bias_pct", "median_height_forest_px_m", "median_height_nonforest_px_m",
                "excluded_by_bias_rule", "excluded"]].to_string())

# %%
p = pd.concat(per_pass, ignore_index=True)
p["w"] = p["n_px"] / (EPS + p["bias"])
g = p.groupby("cell_id")
bio = pd.DataFrame({
    "fh": g.apply(lambda d: np.average(d["fh"], weights=d["w"]), include_groups=False),
    "bias": g.apply(lambda d: np.average(d["bias"], weights=d["w"]), include_groups=False),
    "fh_within_std": g.apply(lambda d: np.average(d["fh_within_std"], weights=d["w"]), include_groups=False),
    # sensitivity check: passes weighted by pixel count only, without ESA's 1/(0.01 + bias) weight
    "fh_unweighted": g.apply(lambda d: np.average(d["fh"], weights=d["n_px"]), include_groups=False),
    "fh_between_pass_std": g["fh"].std(ddof=0),
    "n_passes": g.size(),
})
bio["fh_within_cv"] = bio["fh_within_std"] / bio["fh"]  # structural complexity (Valbuena et al. 2020)
print(f"{len(bio)} cells with BIOMASS forest height (forest pixels only) from {products['excluded'].eq(False).sum()} products")

# %% [markdown]
# ## GEDI footprints per cell
#
# GEDI Version 3. Common selection for both products: `degrade_flag` = 0, full-power beams (the GEDI L2 User
# Guide V3: "GEDI power beams should be used" in dense forest), footprint in a forest block. Product flags, as
# defined in the User Guide V3 pseudo-code: L2A `l2a_quality_flag_rel3` = 1, which already requires
# `sensitivity` > 0.98 over tropical forest (0.95 elsewhere on land); L2B `l2b_quality_flag_rel3` = 1 (adds land,
# < 50 % urban, canopy < 150 m) and `l2_algrunflag` = 1. Note that the V3 root `quality_flag` only means "likely
# invalid waveform" and is not used.
# Night shots (`solar_elevation` < 0) are kept and flagged; `03` checks that the height result holds on night
# shots alone.
#
# Per cell:
# - **L2A:** median RH98 (a second, independent estimate of ecosystem height), its spread, the shot count.
# - **L2B:** median `cover` (ecosystem cover), median `fhd_normal` (structural complexity), and the mean plant
#   area volume density profile over the footprints, normalised to **percent per height bin**: the relative
#   vertical distribution of plant-area volume. `pavd_z` values of −9999 (no data) are ignored.

# %%
def select(df: pd.DataFrame, flags: dict) -> pd.DataFrame:
    keep = (df["degrade_flag"] == 0) & df["beam_type"].str.contains("full power", case=False)
    for col, val in flags.items():
        keep &= df[col] == val
    out = df[keep].copy()
    out = out[in_forest(out["lon"].to_numpy(), out["lat"].to_numpy())]
    out["cell_id"] = nested.lonlat_to_healpix(out["lon"].to_numpy(), out["lat"].to_numpy(), np.uint8(DEPTH),
                                              ellipsoid=ELLIPSOID).astype("uint64")
    out["night"] = out["solar_elevation"] < 0
    print(f"  kept {len(out)} of {len(df)} footprints ({100*out['night'].mean():.0f} % at night)")
    return out


q = lambda x, k: np.nanpercentile(x, k)
print("GEDI L2A:")
ga = select(pd.read_parquet(RAW / "gedi_l2a_beni.parquet"), {"l2a_quality_flag_rel3": 1})
gg = ga.groupby("cell_id")
ged = pd.DataFrame({
    "rh98_median": gg["rh98"].median(),
    "rh98_iqr": gg["rh98"].agg(lambda x: q(x, 75) - q(x, 25)),
    "rh98_median_night": ga[ga["night"]].groupby("cell_id")["rh98"].median(),
    "n_shots": gg.size(),
})

print("GEDI L2B:")
gb = select(pd.read_parquet(RAW / "gedi_l2b_beni.parquet"), {"l2b_quality_flag_rel3": 1, "l2_algrunflag": 1})
DZ = float(gb["dz"].iloc[0])
assert np.allclose(gb["dz"], DZ), "GEDI L2B profiles with different vertical steps"
pcols = sorted(c for c in gb if c.startswith("pavd_"))
gb[pcols] = gb[pcols].where(gb[pcols] > -9999)
for c in ("cover", "fhd_normal"):
    gb[c] = gb[c].where(gb[c] > -9999)
bb = gb.groupby("cell_id")
l2b = pd.DataFrame({"cover_median": bb["cover"].median(), "fhd_median": bb["fhd_normal"].median(),
                    "n_shots_l2b": bb.size()})
pavd_mean = bb[pcols].mean()
total = pavd_mean.sum(axis=1)
profile_pct = pavd_mean.div(total.where(total > 0), axis=0) * 100
print(f"profile: {len(pcols)} bins of {DZ:g} m, in {profile_pct.notna().all(axis=1).sum()} cells")

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
cells = np.array(sorted(set(bio.index) | set(ged.index) | set(l2b.index)), dtype="uint64")
T = pd.DataFrame(index=pd.Index(cells, name="cell_id")).join(bio).join(ged).join(l2b).join(fire).join(tree)
P = profile_pct.reindex(T.index).to_numpy("float32")

FH_DEF = ("BIOMASS L2A forest height: 'forest upper canopy height (H100 Standard)' (BIOMASS Forest Height ATBD "
          "BIO-BPS-FH-ATBD-ARE-10343 v2.2.0, 2026-03-13, sec. 3.5.1); 'Top Canopy Height (TCH)' (BIOMASS Forest "
          "Height Products Format Specification BIO-BPS-FHPFD-ARE-010256 v3.4.0, sec. 4.2)")
BIAS_DEF = ("BIOMASS L2A forest height quality: 'a percentage bias value for each of the Forest Height image pixel, "
            "indicating the inversion performance' (Format Specification v3.4.0, sec. 4.2); computed as "
            "|k_hb - k_h| / k_h * 100 (ATBD eq. 3.22). Lower is better.")
RH_DEF = ("GEDI L2A V003 rh: 'Relative height metrics at 1 % interval' (GEDI L2A V3 product data dictionary); "
          "RH100 = elev_highestreturn - elev_lowestmode (GEDI L2 User Guide V2.1). rh98 is the height above the "
          "lowest mode at which 98 % of the returned waveform energy is reached.")
COVER_DEF = ("GEDI L2B cover: 'Total canopy cover, defined as the percent of the ground covered by the vertical "
             "projection of canopy material' (GEDI L2B V3 product data dictionary); valid range 0-1, so stored as a "
             "fraction despite the word 'percent'.")
FHD_DEF = ("GEDI L2B fhd_normal: 'Foliage height diversity index calculated by vertical foliage profile normalized "
           "by total plant area index' (GEDI L2B V3 product data dictionary).")
PAVD_DEF = ("GEDI L2B V003 pavd_z: 'Vertical Plant Area Volume Density profile from ground (z=0) to canopy top with "
            "a vertical step size of dZ', m2 m-3 (GEDI L2B V3 product data dictionary).")
NO_STD = "No CF standard name exists for this quantity (CF standard name table v95)."


def var(col, attrs, dtype="float32"):
    return ("cells", T[col].to_numpy(dtype=dtype), {**attrs, "grid_mapping": "crs"})


ds = xr.Dataset(
    {
        "biomass_forest_height": var("fh", {
            "standard_name": "canopy_height", "units": "m", "long_name": "BIOMASS forest height (H100)",
            "definition": FH_DEF, "support": "200 m radar pixels (posted every ~90 m) on forest blocks (WorldCover tree cover >= 50 %), area-weighted mean over the cell",
            "statistic": "per pass: area-weighted cell mean; across passes: weighted mean, weights pixel_count/(0.01+bias)",
            "cell_methods": "area: mean", "ancillary_variables": "biomass_fh_bias biomass_n_passes",
            "source": "ESA BIOMASS L2A FP_FH__L2A via ESA MAAP (collection BiomassLevel2a)"}),
        "biomass_forest_height_unweighted": var("fh_unweighted", {
            "standard_name": "canopy_height", "units": "m",
            "long_name": "BIOMASS forest height (H100), passes weighted by pixel count only (sensitivity check)",
            "definition": FH_DEF, "cell_methods": "area: mean"}),
        "biomass_fh_bias": var("bias", {
            "units": "percent", "long_name": "BIOMASS forest-height inversion bias (quality index)",
            "definition": BIAS_DEF, "comment": NO_STD, "statistic": "same weighting as biomass_forest_height"}),
        "biomass_fh_within_cell_std": var("fh_within_std", {
            "units": "m", "long_name": "standard deviation of BIOMASS forest height within the cell (weighted over passes)",
            "comment": "structural complexity: variability in height (Valbuena et al. 2020)"}),
        "biomass_fh_within_cell_cv": var("fh_within_cv", {
            "units": "1", "long_name": "coefficient of variation of BIOMASS forest height within the cell",
            "comment": "structural complexity: variability in height (Valbuena et al. 2020)"}),
        "biomass_fh_between_pass_std": var("fh_between_pass_std", {
            "units": "m", "long_name": "spread of cell-mean BIOMASS forest height across passes"}),
        "biomass_n_passes": var("n_passes", {"standard_name": "number_of_observations", "units": "1",
                                             "long_name": "BIOMASS passes contributing to the cell"}),
        "gedi_rh98": var("rh98_median", {
            "standard_name": "canopy_height", "units": "m", "long_name": "GEDI relative height RH98, cell median",
            "definition": RH_DEF, "support": "~25 m lidar footprints inside the cell",
            "statistic": "median over kept footprints (l2a_quality_flag_rel3=1, degrade_flag=0, full-power beams, forest block)",
            "cell_methods": "area: median", "ancillary_variables": "gedi_n_shots gedi_rh98_iqr",
            "source": "GEDI L2A V003 doi:10.5067/GEDI/GEDI02_A.003, subset by NASA Harmony"}),
        "gedi_rh98_iqr": var("rh98_iqr", {"units": "m", "long_name": "interquartile range of GEDI RH98 in the cell"}),
        "gedi_rh98_night": var("rh98_median_night", {"units": "m", "standard_name": "canopy_height",
                                                     "long_name": "GEDI RH98, cell median of night shots only",
                                                     "definition": RH_DEF}),
        "gedi_n_shots": var("n_shots", {"standard_name": "number_of_observations", "units": "1",
                                        "long_name": "kept GEDI footprints in the cell"}),
        "gedi_cover": var("cover_median", {
            "units": "1", "long_name": "GEDI L2B total canopy cover, cell median", "definition": COVER_DEF,
            "support": "~25 m lidar footprints in forest blocks inside the cell", "statistic": "median over kept footprints",
            "comment": NO_STD, "source": "GEDI L2B V003 doi:10.5067/GEDI/GEDI02_B.003, subset by NASA Harmony"}),
        "gedi_fhd_normal": var("fhd_median", {
            "units": "1", "long_name": "GEDI L2B foliage height diversity, cell median", "definition": FHD_DEF,
            "statistic": "median over kept footprints", "comment": NO_STD}),
        "gedi_n_shots_l2b": var("n_shots_l2b", {"standard_name": "number_of_observations", "units": "1",
                                                "long_name": "kept GEDI L2B footprints in the cell"}),
        "gedi_relative_vertical_profile": (("cells", "height_bin"), P, {
            "units": "percent", "grid_mapping": "crs",
            "long_name": "relative vertical distribution of plant area volume: percent of the cell's mean GEDI PAVD profile in each height bin",
            "definition": PAVD_DEF, "statistic": "mean pavd_z over kept footprints, then normalised to sum to 100 over height bins",
            "comment": "Plant-area volume only; the EBV specification also names biomass, which this variable does not carry."}),
        "tree_cover_fraction": var("tree_cover_fraction", {
            "units": "1", "long_name": "share of the cell classified 'Tree cover' (class 10) by ESA WorldCover 2021",
            "source": "ESA WorldCover 10 m 2021 v200 doi:10.5281/zenodo.7254221",
            "comment": f"ecosystem focus group 'forest': cells with tree_cover_fraction >= {FOREST_MIN}"}),
        "burned_share_2024": var("burned_share_2024", {
            "standard_name": "burned_area_fraction", "units": "1", "cell_methods": "area: mean time: maximum",
            "long_name": "share of observed, burnable 300 m pixels burned at least once in 2024",
            "source": "ESA Fire_cci SYN burned area pixel v1.1 doi:10.5285/d441079fc77f49fabeb41330612b252f"}),
        "crs": ((), np.int8(0), cf_grid_mapping_attrs(DEPTH)),
    },
    coords={"cell_ids": ("cells", cells, {"standard_name": "healpix_index", "units": "1"}),
            "height_bin": ("height_bin", (np.arange(len(pcols)) + 0.5) * DZ,
                           {"units": "m", "long_name": "centre of the height bin above ground", "bounds": "height_bin_bounds"}),
            "height_bin_bounds": (("height_bin", "nv"), np.stack([np.arange(len(pcols)) * DZ,
                                                                (np.arange(len(pcols)) + 1) * DZ], axis=1), {"units": "m"})},
)
ds.attrs.update(dggs_attrs(DEPTH))
ds.attrs.update({"Conventions": "CF-1.8", "title": "Beni lowlands: inputs for the EBV Ecosystem Vertical Profile on HEALPix",
                 "region_bbox_lonlat": list(BBOX), "forest_min_tree_cover_fraction": FOREST_MIN,
                 "gedi_first_shot": f"{min(ga.time.min(), gb.time.min()):%Y-%m-%d}", "gedi_last_shot": f"{max(ga.time.max(), gb.time.max()):%Y-%m-%d}", "producer": f"healpix-connector {healpix_connector.__version__}",
                 "biomass_products": products.to_json(orient="records")})
STORE = CLEAN / "beni_canopy_height.zarr"
ds.to_zarr(STORE, group=f"measurements/canopy_height/{DEPTH}", mode="w", zarr_format=3, consolidated=False)
products.to_csv(CLEAN / "biomass_products.csv", index=False)
ds
