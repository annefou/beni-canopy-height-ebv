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
# The EBV dataset *Ecosystem Vertical Profile* for forest cells, drawn as true WGS84 HEALPix cell outlines.
# Top: ecosystem height (BIOMASS), ecosystem cover (GEDI), structural complexity (BIOMASS height CV).
# Bottom: relative vertical profile (GEDI), BIOMASS against GEDI height, disagreement by BIOMASS bias index.

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

RESULTS, FIGURES = Path("../results"), Path("../figures")
FIGURES.mkdir(exist_ok=True)
DEPTH, BBOX = 11, (-67.5, -15.5, -64.5, -12.5)
plt.style.use("seaborn-v0_8-whitegrid")

ebv = xr.open_zarr(RESULTS / "beni_ecosystem_vertical_profile.zarr", group=f"measurements/canopy_height/{DEPTH}",
                   consolidated=False).load()
cal = pd.read_parquet(RESULTS / "comparison_cells.parquet")
S = json.loads((RESULTS / "summary.json").read_text())


def polys(cell_ids):
    lon, lat = nested.vertices(np.asarray(cell_ids, dtype="uint64"), np.uint8(DEPTH), ellipsoid=ELLIPSOID)
    return np.stack([np.where(lon > 180, lon - 360, lon), lat], axis=-1)


def cell_map(ax, values, title, label, cmap="YlGn", vmin=None, vmax=None):
    vals = np.ma.masked_invalid(values)
    pc = PolyCollection(polys(ebv.cell_ids), array=vals, cmap=cmap, edgecolors="none",
                        norm=plt.Normalize(vmin if vmin is not None else float(vals.min()),
                                           vmax if vmax is not None else float(np.nanpercentile(values, 99))))
    ax.add_collection(pc)
    ax.set(xlim=(BBOX[0], BBOX[2]), ylim=(BBOX[1], BBOX[3]), aspect="equal", title=title)
    plt.colorbar(pc, ax=ax, shrink=0.75, label=label)


# %%
fig, axs = plt.subplots(2, 3, figsize=(15, 9.5), constrained_layout=True)
cell_map(axs[0, 0], ebv["ecosystem_height"], "Ecosystem height (BIOMASS H100)", "m", vmin=0, vmax=35)
cell_map(axs[0, 1], ebv["ecosystem_cover"], "Ecosystem cover (GEDI L2B)", "fraction", vmin=0, vmax=1)
cell_map(axs[0, 2], ebv["structural_complexity_height_cv"], "Structural complexity (height CV)", "1",
         cmap="PuBu", vmin=0)

ax = axs[1, 0]
p = ebv["relative_vertical_profile"]
h = ebv["height_bin"].values
q25, q50, q75 = (np.nanpercentile(p.values, k, axis=0) for k in (25, 50, 75))
ax.fill_betweenx(h, q25, q75, color="#009E73", alpha=0.3, label="25–75 % of forest cells")
ax.plot(q50, h, color="#009E73", lw=2, label="median")
top = h[np.flatnonzero(q75 > 0.5)].max() + 10 if (q75 > 0.5).any() else h.max()  # skip empty upper bins
ax.set(xlabel="share of plant-area volume (%)", ylabel="height above ground (m)", ylim=(0, top),
       title=f"Relative vertical profile (GEDI L2B), {S['ebv_cells']['profile']} cells")
ax.legend(fontsize=8)

ax = axs[1, 1]
ax.scatter(cal["biomass_forest_height"], cal["gedi_rh98"], s=6, alpha=0.4, color="#0072B2")
lim = [0, max(cal["biomass_forest_height"].max(), cal["gedi_rh98"].max()) * 1.05]
ax.plot(lim, lim, color="0.4", lw=1, ls="--", label="1:1")
r = S["height_relation"]
ax.plot(lim, [r["intercept_m"] + r["slope"] * x for x in lim], color="#D55E00", lw=1.5,
        label=f"{r['intercept_m']:.1f} + {r['slope']:.2f}·H100 (CV RMSE {r['cv_rmse_m']:.1f} m)")
ax.set(xlim=lim, ylim=lim, xlabel="BIOMASS H100 (m)", ylabel="GEDI RH98 (m)",
       title=f"Two estimates of ecosystem height (n = {len(cal)}, Spearman {S['agreement_all_shots']['spearman']:.2f})")
ax.legend(loc="upper left", fontsize=8)

ax = axs[1, 2]
order = ["low bias", "mid bias", "high bias"]
ax.boxplot([cal.loc[cal["bias_tercile"] == t, "abs_diff"] for t in order], showfliers=False)
ax.set_xticks([1, 2, 3], order)
ax.set(ylabel="|BIOMASS − GEDI| (m)",
       title=f"Disagreement by BIOMASS bias index (Spearman {S['bias_index_vs_disagreement']['spearman']:.2f})")
fig.suptitle("EBV Ecosystem Vertical Profile, forest, Beni lowlands, WGS84 HEALPix depth 11 (~3.2 km). Data: ESA BIOMASS "
             "L2A FP_FH (ESA MAAP); GEDI L2A/L2B V002; ESA WorldCover 2021; ESA Fire_cci v1.1", fontsize=9)
fig.savefig(FIGURES / "main_result.png", dpi=150)
fig.savefig(FIGURES / "main_result.pdf")
plt.show()
