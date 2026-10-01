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
# # 04 — Figures
# Top: BIOMASS forest height, GEDI RH98 and the canopy-height EBV dataset (Ecosystem Vertical Profile) with its uncertainty, drawn as true WGS84
# HEALPix cell outlines. Bottom: BIOMASS against GEDI on the calibration cells, and disagreement by BIOMASS bias
# index tercile.

# %%
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr
from healpix_connector.conventions import ELLIPSOID
from healpix_geo import nested
from matplotlib.collections import PolyCollection

CLEAN, RESULTS, FIGURES = Path("../data/clean"), Path("../results"), Path("../figures")
FIGURES.mkdir(exist_ok=True)
DEPTH, BBOX = 11, (-67.5, -15.5, -64.5, -12.5)
plt.style.use("seaborn-v0_8-whitegrid")

grp = f"measurements/canopy_height/{DEPTH}"
src = xr.open_zarr(CLEAN / "beni_canopy_height.zarr", group=grp, consolidated=False).load()
ebv = xr.open_zarr(RESULTS / "beni_canopy_height_ebv.zarr", group=grp, consolidated=False).load()
cal = pd.read_parquet(RESULTS / "calibration_cells.parquet")
S = json.loads((RESULTS / "summary.json").read_text())


def polys(cell_ids):
    lon, lat = nested.vertices(np.asarray(cell_ids, dtype="uint64"), np.uint8(DEPTH), ellipsoid=ELLIPSOID)
    return np.stack([np.where(lon > 180, lon - 360, lon), lat], axis=-1)


def cell_map(ax, cell_ids, values, title, cmap="YlGn", vmin=0, vmax=35):
    pc = PolyCollection(polys(cell_ids), array=np.ma.masked_invalid(values), cmap=cmap, edgecolors="none",
                        norm=plt.Normalize(vmin, vmax))
    ax.add_collection(pc)
    ax.set(xlim=(BBOX[0], BBOX[2]), ylim=(BBOX[1], BBOX[3]), aspect="equal", title=title)
    plt.colorbar(pc, ax=ax, shrink=0.75, label="m")


# %%
fig, axs = plt.subplots(2, 3, figsize=(15, 9.5), constrained_layout=True)
cell_map(axs[0, 0], src.cell_ids, src["biomass_forest_height"], "BIOMASS forest height (H100), 2026")
cell_map(axs[0, 1], src.cell_ids, src["gedi_rh98"], "GEDI RH98, cell median, 2019-2025")
cell_map(axs[0, 2], ebv.cell_ids, ebv["canopy_height"], "EBV dataset: canopy height (GEDI RH98 scale)")

ax = axs[1, 0]
ax.scatter(cal["biomass_forest_height"], cal["gedi_rh98"], s=6, alpha=0.4, color="#0072B2")
lim = [0, max(cal["biomass_forest_height"].max(), cal["gedi_rh98"].max()) * 1.05]
ax.plot(lim, lim, color="0.4", lw=1, ls="--", label="1:1")
m = S["calibration"]
ax.plot(lim, [m["intercept_m"] + m["slope"] * v for v in lim], color="#D55E00", lw=1.5,
        label=f"fit: {m['intercept_m']:.1f} + {m['slope']:.2f}·H100 (CV RMSE {m['cv_rmse_m']:.1f} m)")
ax.set(xlim=lim, ylim=lim, xlabel="BIOMASS forest height H100 (m)", ylabel="GEDI RH98 (m)",
       title=f"Calibration cells (n = {len(cal)}), Spearman {S['agreement_all_shots']['spearman']:.2f}")
ax.legend(loc="upper left", fontsize=8)

ax = axs[1, 1]
order = ["low bias", "mid bias", "high bias"]
ax.boxplot([cal.loc[cal["bias_tercile"] == t, "abs_diff"] for t in order], showfliers=False)
ax.set_xticks([1, 2, 3], order)
ax.set(ylabel="|BIOMASS − GEDI| (m)",
       title=f"Disagreement by BIOMASS bias index (Spearman {S['bias_index_vs_disagreement']['spearman']:.2f})")

cell_map(axs[1, 2], ebv.cell_ids, ebv["canopy_height_uncertainty"], "EBV uncertainty (1 σ)", cmap="magma_r",
         vmin=0, vmax=float(np.nanpercentile(ebv["canopy_height_uncertainty"], 99)))
fig.suptitle("Beni lowlands on WGS84 HEALPix depth 11 (~3.2 km). Data: ESA BIOMASS L2A FP_FH (ESA MAAP); "
             "GEDI L2A V002 doi:10.5067/GEDI/GEDI02_A.002; ESA Fire_cci v1.1", fontsize=9)
fig.savefig(FIGURES / "main_result.png", dpi=150)
fig.savefig(FIGURES / "main_result.pdf")
plt.show()
