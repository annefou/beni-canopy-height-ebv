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
# # 03 — Analysis: an EBV dataset for *Ecosystem Vertical Profile*
#
# **Question (PICO).** Population: forest cells (ESA WorldCover tree cover ≥ 50 %) of the Beni lowlands on HEALPix
# depth 11. Intervention: ESA BIOMASS L2A forest height (H100, 2026). Comparator: GEDI L2A RH98 (2019–2025).
# Outcome: agreement (bias, error, rank correlation) between the two estimates of ecosystem height.
#
# **What is produced.** A dataset for the GEO BON EBV *Ecosystem Vertical Profile* in the forest focus group,
# carrying what its specification asks for (see `02`): ecosystem height, ecosystem cover, structural complexity,
# and the relative vertical profile.
#
# Steps:
# 1. **Agreement** between BIOMASS and GEDI heights on forest cells where both exist, fire did not intervene
#    (burned share 2024 ≤ 5 %), and at least 5 kept GEDI shots fall.
# 2. **Does the BIOMASS quality index mean what the documentation says?** If it is a bias (lower is better),
#    disagreement with GEDI should grow with it.
# 3. **Relation between the two heights** GEDI RH98 ≈ a + b · BIOMASS H100, by spatial block cross-validation
#    (blocks are depth-7 parent cells, ~51 km). It is a diagnostic: H100 is already the quantity the EBV defines
#    as ecosystem height ("top of canopy height in forests"), so it is **not** converted to the GEDI scale.
# 4. **The EBV dataset**, with per-cell uncertainty for height.
#
# Descriptive, one region, one BIOMASS season: the result says how the products relate here, not globally.

# %%
import json
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
from healpix_connector.dggs_zarr import dggs_attrs
from scipy import stats

CLEAN = Path("../data/clean")
RESULTS = Path("../results")
RESULTS.mkdir(parents=True, exist_ok=True)
DEPTH, BLOCK_DEPTH = 11, 7
MIN_SHOTS, MAX_BURNED = 5, 0.05
GROUP = f"measurements/canopy_height/{DEPTH}"

ds = xr.open_zarr(CLEAN / "beni_canopy_height.zarr", group=GROUP, consolidated=False).load()
FOREST_MIN = float(ds.attrs["forest_min_tree_cover_fraction"])
T = ds.drop_vars(["crs", "gedi_relative_vertical_profile", "height_bin_bounds"]).drop_dims("height_bin").to_dataframe()
T = T.set_index("cell_ids")
forest = T["tree_cover_fraction"] >= FOREST_MIN

both = forest & T["biomass_forest_height"].notna() & T["gedi_rh98"].notna()
cal = T[both & (T["gedi_n_shots"] >= MIN_SHOTS) & (T["burned_share_2024"].fillna(0) <= MAX_BURNED)].copy()
print(f"{forest.sum()} forest cells; {both.sum()} with both heights; {len(cal)} usable for comparison "
      f"(>= {MIN_SHOTS} shots, burned share 2024 <= {MAX_BURNED})")
if len(cal) < 30:
    raise SystemExit(f"Only {len(cal)} comparison cells: too few for a cross-validated relation. "
                     "Check the GEDI download (01) and the selection thresholds above.")

# %% [markdown]
# ## 1. Agreement

# %%
def agreement(x: pd.Series, y: pd.Series) -> dict:
    d = x - y
    return {"n_cells": int(len(d)), "mean_difference_m": float(d.mean()), "rmse_m": float(np.sqrt((d**2).mean())),
            "spearman": float(stats.spearmanr(x, y).statistic), "pearson": float(stats.pearsonr(x, y).statistic)}


agree = agreement(cal["biomass_forest_height"], cal["gedi_rh98"])
night = cal.dropna(subset=["gedi_rh98_night"])
agree_night = agreement(night["biomass_forest_height"], night["gedi_rh98_night"])
print(json.dumps({"all_shots": agree, "night_shots": agree_night}, indent=1))

# %% [markdown]
# ## 2. Does disagreement grow with the BIOMASS bias index?

# %%
cal["abs_diff"] = (cal["biomass_forest_height"] - cal["gedi_rh98"]).abs()
cal["bias_tercile"] = pd.qcut(cal["biomass_fh_bias"], 3, labels=["low bias", "mid bias", "high bias"])
by_bias = cal.groupby("bias_tercile", observed=True).agg(
    bias_pct_median=("biomass_fh_bias", "median"), abs_diff_median_m=("abs_diff", "median"),
    n_cells=("abs_diff", "size"))
rho_bias = stats.spearmanr(cal["biomass_fh_bias"], cal["abs_diff"])
print(by_bias.to_string())
print(f"Spearman(bias index, |BIOMASS - GEDI|) = {rho_bias.statistic:.2f} (p = {rho_bias.pvalue:.2g})")

# %% [markdown]
# ## 3. Relation between the two heights (diagnostic), spatial block cross-validation

# %%
cal["block"] = cal.index.to_numpy(dtype="uint64") >> np.uint64(2 * (DEPTH - BLOCK_DEPTH))
blocks = cal["block"].unique()
rng = np.random.default_rng(20261001)
cal["fold"] = cal["block"].map(dict(zip(blocks, rng.permutation(len(blocks)) % 5)))
pred = pd.Series(np.nan, index=cal.index)
for k in range(5):
    tr, te = cal["fold"] != k, cal["fold"] == k
    f = stats.linregress(cal.loc[tr, "biomass_forest_height"], cal.loc[tr, "gedi_rh98"])
    pred[te] = f.intercept + f.slope * cal.loc[te, "biomass_forest_height"]
cv_res = cal["gedi_rh98"] - pred
fit = stats.linregress(cal["biomass_forest_height"], cal["gedi_rh98"])
relation = {"intercept_m": float(fit.intercept), "slope": float(fit.slope), "r2_in_sample": float(fit.rvalue**2),
            "cv_rmse_m": float(np.sqrt((cv_res**2).mean())), "cv_mean_residual_m": float(cv_res.mean()),
            "n_blocks": int(len(blocks)), "block_depth": BLOCK_DEPTH, "folds": 5}
print(json.dumps(relation, indent=1))

# %% [markdown]
# ## 4. The EBV dataset
#
# Forest cells only (the ecosystem focus group). Per cell:
#
# | Variable | EBV component | Source |
# |---|---|---|
# | `ecosystem_height` | ecosystem height | BIOMASS H100, unchanged |
# | `ecosystem_height_uncertainty` | its 1 σ | sqrt(between-pass std² + cv_rmse²): pass-to-pass precision plus the random part of the disagreement with GEDI (the systematic part, intercept and slope, reflects the two definitions and is reported, not counted as error) |
# | `ecosystem_height_gedi` | ecosystem height, independent estimate | GEDI RH98 cell median |
# | `ecosystem_cover` | ecosystem cover | GEDI L2B `cover` cell median |
# | `structural_complexity_height_cv` | structural complexity | coefficient of variation of BIOMASS height within the cell |
# | `structural_complexity_fhd` | structural complexity | GEDI L2B foliage height diversity, cell median |
# | `relative_vertical_profile` | the profile | GEDI L2B plant area volume density, percent per height bin |
#
# GEDI components exist only in cells with kept footprints. Cells burned in 2024 keep their values and are flagged.

# %%
F = T[forest].copy()
F["sigma"] = np.sqrt(F["biomass_fh_between_pass_std"].fillna(0) ** 2 + relation["cv_rmse_m"] ** 2)
F.loc[F["biomass_forest_height"].isna(), "sigma"] = np.nan
F["burned_flag"] = (F["burned_share_2024"].fillna(0) > MAX_BURNED).astype("int8")
prof = ds["gedi_relative_vertical_profile"].sel(cells=np.isin(ds.cell_ids, F.index.to_numpy()))
assert np.array_equal(prof.cell_ids.values, F.index.to_numpy())

BIOMASS_TIME = "BIOMASS: " + ", ".join(sorted({p["start"][:10] for p in json.loads(ds.attrs["biomass_products"])
                                              if not p["excluded"]}))
GEDI_TIME = f"GEDI V003: {ds.attrs['gedi_first_shot']} to {ds.attrs['gedi_last_shot']} (kept footprints)"


def v(col: str, attrs: dict, dtype: str = "float32"):
    return ("cells", F[col].to_numpy(dtype), {**attrs, "grid_mapping": "crs"})


src = {k: ds[k].attrs for k in ds.data_vars}
ebv = xr.Dataset(
    {
        "ecosystem_height": v("biomass_forest_height", {
            "standard_name": "canopy_height", "units": "m", "long_name": "ecosystem height (top of canopy height)",
            "ebv_component": "ecosystem height (Valbuena et al. 2020)", "definition": src["biomass_forest_height"]["definition"],
            "time_coverage": BIOMASS_TIME, "ancillary_variables": "ecosystem_height_uncertainty biomass_n_passes"}),
        "ecosystem_height_uncertainty": v("sigma", {
            "units": "m", "long_name": "1-sigma uncertainty of ecosystem_height",
            "comment": "sqrt(between-pass std^2 + cv_rmse^2); cv_rmse from the spatially cross-validated relation to GEDI RH98"}),
        "ecosystem_height_gedi": v("gedi_rh98", {
            "standard_name": "canopy_height", "units": "m", "long_name": "ecosystem height, independent estimate (GEDI RH98)",
            "ebv_component": "ecosystem height (Valbuena et al. 2020)", "definition": src["gedi_rh98"]["definition"],
            "time_coverage": GEDI_TIME}),
        "ecosystem_cover": v("gedi_cover", {
            "units": "1", "long_name": "ecosystem cover (GEDI L2B total canopy cover)",
            "ebv_component": "ecosystem cover (Valbuena et al. 2020)", "definition": src["gedi_cover"]["definition"],
            "time_coverage": GEDI_TIME}),
        "structural_complexity_height_cv": v("biomass_fh_within_cell_cv", {
            "units": "1", "long_name": "structural complexity: coefficient of variation of BIOMASS height within the cell",
            "ebv_component": "structural complexity (Valbuena et al. 2020)", "time_coverage": BIOMASS_TIME}),
        "structural_complexity_fhd": v("gedi_fhd_normal", {
            "units": "1", "long_name": "structural complexity: GEDI L2B foliage height diversity",
            "ebv_component": "structural complexity (Valbuena et al. 2020)", "definition": src["gedi_fhd_normal"]["definition"],
            "time_coverage": GEDI_TIME}),
        "relative_vertical_profile": (("cells", "height_bin"), prof.values, {
            **prof.attrs, "grid_mapping": "crs", "time_coverage": GEDI_TIME,
            "ebv_component": "relative vertical distribution of volume (EuropaBON D4.1)"}),
        "burned_2024_flag": ("cells", F["burned_flag"].to_numpy(), {
            "flag_values": np.array([0, 1], dtype="int8"), "flag_meanings": "not_burned burned_over_5_percent_in_2024",
            "long_name": "cell burned between GEDI and BIOMASS acquisitions (Fire_cci 2024)"}),
        "tree_cover_fraction": v("tree_cover_fraction", src["tree_cover_fraction"]),
        "biomass_n_passes": v("biomass_n_passes", {"standard_name": "number_of_observations", "units": "1"}),
        "crs": ds["crs"],
    },
    coords={"cell_ids": ("cells", F.index.to_numpy("uint64"), {"standard_name": "healpix_index", "units": "1"}),
            "height_bin": ds["height_bin"], "height_bin_bounds": ds["height_bin_bounds"]},
)
ebv.attrs.update(dggs_attrs(DEPTH))
ebv.attrs.update({
    "Conventions": "CF-1.8",
    "title": "Ecosystem Vertical Profile (EBV dataset, prototype), forest, Beni lowlands, from ESA BIOMASS and GEDI",
    "ebv_class": "Ecosystem Structure",
    "ebv_name": "Ecosystem Vertical Profile",
    "ebv_source": "GEO BON EBV list, 6 classes and 21 EBV names (https://geobon.org/ebvs/what-are-ebvs/, read 2026-10-01)",
    "ebv_specification": ("EuropaBON D4.1 (2022): 'Percentage of the relative vertical distribution of volume and "
                          "biomass in the ecosystem focus group'; traits after Valbuena et al. 2020, "
                          "doi:10.1016/j.tree.2020.03.006"),
    "ebv_entity": f"ecosystem focus group 'forest': ESA WorldCover 2021 class 10 'Tree cover' >= {FOREST_MIN:.0%} of the cell",
    "ebv_gaps": ("vertical profile is of plant-area volume (GEDI), not biomass; profile and cover only where GEDI "
                 "footprints fall; one BIOMASS season; no in-situ heights for validation"),
    "remote_sensing_biodiversity_product": "Vegetation height",
    "remote_sensing_enabled_biodiversity_variable": "Habitat structure",
    "skidmore_2021_mapping": "Skidmore et al. 2021, doi:10.1038/s41559-021-01451-x, Table 2 no. 14",
    **{f"height_relation_{k}": val for k, val in relation.items()},
})
ebv.to_zarr(RESULTS / "beni_ecosystem_vertical_profile.zarr", group=GROUP, mode="w", zarr_format=3, consolidated=False)

has = lambda c: int(F[c].notna().sum())
summary = {"agreement_all_shots": agree, "agreement_night_shots": agree_night,
           "bias_index_vs_disagreement": {"spearman": float(rho_bias.statistic), "p": float(rho_bias.pvalue),
                                          "by_tercile": by_bias.reset_index().astype({"bias_tercile": str}).to_dict("records")},
           "height_relation": relation,
           "ebv_cells": {"forest": int(len(F)), "height": has("biomass_forest_height"), "height_gedi": has("gedi_rh98"),
                         "cover": has("gedi_cover"), "complexity_cv": has("biomass_fh_within_cell_cv"),
                         "complexity_fhd": has("gedi_fhd_normal"),
                         "profile": int(np.isfinite(prof.values).all(axis=1).sum()),
                         "burned_2024": int(F["burned_flag"].sum())},
           "selection": {"forest_min_tree_cover": FOREST_MIN, "min_gedi_shots": MIN_SHOTS,
                         "max_burned_share_2024": MAX_BURNED}}
(RESULTS / "summary.json").write_text(json.dumps(summary, indent=1))
pd.json_normalize(summary, sep=".").T.rename(columns={0: "value"}).to_csv(RESULTS / "summary.csv")
cal.to_parquet(RESULTS / "comparison_cells.parquet")
print(json.dumps(summary, indent=1))
