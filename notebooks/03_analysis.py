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
# # 03 — Analysis: from BIOMASS forest height to a canopy-height EBV
#
# **Question (PICO).** Population: forest cells of the Beni lowlands on HEALPix depth 11. Intervention: ESA BIOMASS
# L2A forest height (H100, 2026). Comparator: GEDI L2A RH98 (2019–2025). Outcome: agreement (bias, error, rank
# correlation), and whether a calibration model turns BIOMASS heights into a canopy-height EBV with stated
# per-cell uncertainty.
#
# Steps:
# 1. **Agreement** on the cells where both exist and fire did not intervene (burned share 2024 ≤ 5 %), with at
#    least 5 kept GEDI shots.
# 2. **Does the BIOMASS quality index mean what the documentation says?** If it is a bias (lower is better),
#    disagreement with GEDI should grow with it.
# 3. **Calibration model** GEDI RH98 ≈ a + b · BIOMASS H100, evaluated by spatial block cross-validation (blocks
#    are depth-7 parent cells, ~51 km, so neighbouring cells never sit on both sides of a split).
# 4. **EBV**: the calibrated height for every BIOMASS cell, with uncertainty from the cross-validated error and
#    the spread between passes.
#
# Descriptive, one region, one BIOMASS season: the result says how the two products relate here, not globally.

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

ds = xr.open_zarr(CLEAN / "beni_canopy_height.zarr", group=f"measurements/canopy_height/{DEPTH}",
                  consolidated=False).load()
T = ds.drop_vars("crs").to_dataframe().set_index("cell_ids")

both = T["biomass_forest_height"].notna() & T["gedi_rh98"].notna()
cal = T[both & (T["gedi_n_shots"] >= MIN_SHOTS) & (T["burned_share_2024"].fillna(0) <= MAX_BURNED)].copy()
print(f"{both.sum()} cells with both heights; {len(cal)} usable for calibration "
      f"(>= {MIN_SHOTS} shots, burned share 2024 <= {MAX_BURNED})")
if len(cal) < 30:
    raise SystemExit(f"Only {len(cal)} calibration cells: too few for a cross-validated model. "
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
# ## 3. Calibration model, spatial block cross-validation

# %%
cal["block"] = cal.index.to_numpy(dtype="uint64") >> np.uint64(2 * (DEPTH - BLOCK_DEPTH))
blocks = cal["block"].unique()
rng = np.random.default_rng(20261001)
fold_of = dict(zip(blocks, rng.permutation(len(blocks)) % 5))
cal["fold"] = cal["block"].map(fold_of)
pred = pd.Series(np.nan, index=cal.index)
for k in range(5):
    tr, te = cal["fold"] != k, cal["fold"] == k
    fit = stats.linregress(cal.loc[tr, "biomass_forest_height"], cal.loc[tr, "gedi_rh98"])
    pred[te] = fit.intercept + fit.slope * cal.loc[te, "biomass_forest_height"]
cv_res = cal["gedi_rh98"] - pred
fit = stats.linregress(cal["biomass_forest_height"], cal["gedi_rh98"])
model = {"intercept_m": float(fit.intercept), "slope": float(fit.slope), "r2_in_sample": float(fit.rvalue**2),
         "cv_rmse_m": float(np.sqrt((cv_res**2).mean())), "cv_mean_residual_m": float(cv_res.mean()),
         "n_blocks": int(len(blocks)), "block_depth": BLOCK_DEPTH, "folds": 5,
         "uncalibrated_rmse_m": agree["rmse_m"]}
print(json.dumps(model, indent=1))

# %% [markdown]
# ## 4. The EBV: calibrated canopy height with per-cell uncertainty
#
# For every cell with BIOMASS forest height: height = a + b · H100. Uncertainty (1 σ) combines the
# cross-validated model error with the spread between passes, propagated through the slope:
# σ = sqrt(cv_rmse² + (b · between-pass std)²). Cells seen by one pass only get the model error alone, and say so
# through `biomass_n_passes`. Cells burned in 2024 keep their value but are flagged: BIOMASS saw them after the fire.

# %%
E = T.dropna(subset=["biomass_forest_height"]).copy()
E["ebv"] = fit.intercept + fit.slope * E["biomass_forest_height"]
E["ebv_sigma"] = np.sqrt(model["cv_rmse_m"] ** 2 + (fit.slope * E["biomass_fh_between_pass_std"].fillna(0)) ** 2)
E["burned_flag"] = (E["burned_share_2024"].fillna(0) > MAX_BURNED).astype("int8")

ebv = xr.Dataset(
    {
        "canopy_height": ("cells", E["ebv"].to_numpy("float32"), {
            "standard_name": "canopy_height", "units": "m", "grid_mapping": "crs",
            "long_name": "canopy height on the GEDI RH98 scale, from BIOMASS forest height",
            "definition": ("Height above the ground at which 98 % of returned lidar energy is reached (GEDI RH98 "
                           "scale), predicted per cell from BIOMASS L2A forest height (H100) by the linear model "
                           "in model_*. Support: HEALPix depth-11 cell."),
            "ancillary_variables": "canopy_height_uncertainty burned_2024_flag biomass_n_passes"}),
        "canopy_height_uncertainty": ("cells", E["ebv_sigma"].to_numpy("float32"), {
            "units": "m", "grid_mapping": "crs", "long_name": "1-sigma uncertainty of canopy_height",
            "comment": "sqrt(cv_rmse^2 + (slope * between-pass std)^2); cv_rmse from spatial block cross-validation"}),
        "burned_2024_flag": ("cells", E["burned_flag"].to_numpy(), {
            "flag_values": np.array([0, 1], dtype="int8"), "flag_meanings": "not_burned burned_over_5_percent_in_2024",
            "long_name": "cell burned between GEDI and BIOMASS acquisitions (Fire_cci 2024)"}),
        "biomass_n_passes": ("cells", E["biomass_n_passes"].to_numpy("float32"), {
            "standard_name": "number_of_observations", "units": "1"}),
        "crs": ds["crs"],
    },
    coords={"cell_ids": ("cells", E.index.to_numpy("uint64"), {"standard_name": "healpix_index", "units": "1"})},
)
ebv.attrs.update(dggs_attrs(DEPTH))
ebv.attrs.update({
    "Conventions": "CF-1.8",
    "title": "Canopy height EBV (prototype), Beni lowlands, from ESA BIOMASS calibrated against GEDI",
    "ebv_class": "Ecosystem structure",
    "ebv_name": "Ecosystem vertical profile",
    "ebv_name_comment": "Mapping to the GEO BON EBV catalogue to be confirmed before publication.",
    **{f"model_{k}": v for k, v in model.items()},
})
ebv.to_zarr(RESULTS / "beni_canopy_height_ebv.zarr", group=f"measurements/canopy_height/{DEPTH}", mode="w",
            zarr_format=3, consolidated=False)

summary = {"agreement_all_shots": agree, "agreement_night_shots": agree_night,
           "bias_index_vs_disagreement": {"spearman": float(rho_bias.statistic), "p": float(rho_bias.pvalue),
                                          "by_tercile": by_bias.reset_index().astype({"bias_tercile": str}).to_dict("records")},
           "calibration": model, "ebv_cells": int(len(E)), "ebv_cells_burned_2024": int(E["burned_flag"].sum()),
           "selection": {"min_gedi_shots": MIN_SHOTS, "max_burned_share_2024": MAX_BURNED}}
(RESULTS / "summary.json").write_text(json.dumps(summary, indent=1))
pd.json_normalize(summary, sep=".").T.rename(columns={0: "value"}).to_csv(RESULTS / "summary.csv")
cal.to_parquet(RESULTS / "calibration_cells.parquet")
print(json.dumps(summary, indent=1))
