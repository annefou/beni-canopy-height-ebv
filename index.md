# beni-canopy-height-ebv

> **Canopy height as an EBV dataset for *Ecosystem Vertical Profile* (EBV class Ecosystem Structure), from ESA BIOMASS calibrated against GEDI** — Beni lowlands, Bolivia.
>
> Question-rooted study (PICO). Foundation reference: Skidmore et al. 2021, *Priority list of biodiversity metrics to observe from space*, [10.1038/s41559-021-01451-x](https://doi.org/10.1038/s41559-021-01451-x).

**Question.** In the forest cells of the Beni lowlands, how well does ESA BIOMASS L2A forest height (H100, 2026) agree with GEDI L2A RH98 (2019–2025), and does a calibration model turn it into an EBV dataset for the GEO BON EBV *Ecosystem Vertical Profile*, with stated per-cell uncertainty? The EBVs themselves are defined by GEO BON (6 classes, 21 EBV names); this study produces a dataset for one of them, it does not define a new EBV.

**Semantics first.** BIOMASS "forest height" is an upper-canopy stand height (H100) from a 200 m radar inversion; GEDI RH98 is a lidar energy percentile over a 25 m footprint. Both fit the CF name `canopy_height`, but they are different quantities, so each variable here carries its definition quoted from its product documentation, and relating one to the other is a model, not an identity. The BIOMASS quality layer is a percentage bias (lower is better).

**What the EBV asks for, and what this dataset carries.** EuropaBON D4.1 (2022) specifies *Ecosystem Vertical Profile* as the "Percentage of the relative vertical distribution of volume and biomass in the ecosystem focus group"; Valbuena et al. 2020 (doi:10.1016/j.tree.2020.03.006) summarise it by ecosystem height, ecosystem cover and structural complexity. Per forest cell (ESA WorldCover 2021 tree cover ≥ 50 %):

| Component | Variable | Source |
|---|---|---|
| Ecosystem height | `ecosystem_height` (+ uncertainty); `ecosystem_height_gedi` | BIOMASS H100; GEDI L2A RH98 |
| Ecosystem cover | `ecosystem_cover` | GEDI L2B `cover` |
| Structural complexity | `structural_complexity_height_cv`; `structural_complexity_fhd` | BIOMASS within-cell CV; GEDI L2B foliage height diversity |
| Relative vertical profile | `relative_vertical_profile` (percent per 5 m bin) | GEDI L2B plant area volume density |

**Gaps, stated in the dataset:** the profile is of plant-area volume, not biomass; GEDI components exist only where footprints fall; one BIOMASS season so far; no in-situ heights for validation.

This repository produces:

- A reproducible computational pipeline (Snakefile + notebooks).
- A FORRT-tagged nanopublication chain on the [Science Live platform](https://platform.sciencelive4all.org), documenting the claim, the replication design, and the outcome with full provenance.
- A Zenodo-archived release (source + container image) with a citable DOI.

## Quick start

```bash
git clone https://github.com/annefou/beni-canopy-height-ebv.git
cd beni-canopy-height-ebv
pixi install
pixi run snakemake --cores 1
```

Or with Docker:

```bash
docker run --rm ghcr.io/annefou/beni-canopy-height-ebv:latest
```

## Structure

- `paper/` — the source paper PDF (drop yours in there).
- `notebooks/` — jupytext `.py` notebooks that drive the pipeline.
- `data/` — downloaded by `notebooks/01_data_download.py`, never committed.
- `nanopubs/` — drafts of the FORRT chain field-by-field, plus the published-URI registry.
- `docs/` — operating manuals (FORRT form fields, chain decision tree, claim-type vocabulary).
- `figures/` — curated figures used in the Jupyter Book.

## Nanopublication chain

The published chain is listed in [`nanopubs/PUBLISHED.md`](nanopubs/PUBLISHED.md). Each step links to its viewer URL on the Science Live platform.

## Citation

If you use this work, please cite both:

- This software: [`CITATION.cff`](CITATION.cff) → DOI [{{ZENODO_DOI}}]({{ZENODO_DOI}}).
- The original paper: [10.1038/s41559-021-01451-x](https://doi.org/10.1038/s41559-021-01451-x).
