# beni-canopy-height-ebv

> **A canopy-height Essential Biodiversity Variable from ESA BIOMASS, calibrated against GEDI** — Beni lowlands, Bolivia.
>
> Question-rooted study (PICO). Foundation reference: Skidmore et al. 2021, *Priority list of biodiversity metrics to observe from space*, [10.1038/s41559-021-01451-x](https://doi.org/10.1038/s41559-021-01451-x).

**Question.** In the forest cells of the Beni lowlands, how well does ESA BIOMASS L2A forest height (H100, 2026) agree with GEDI L2A RH98 (2019–2025), and does a calibration model turn it into a canopy-height EBV with stated per-cell uncertainty?

**Semantics first.** BIOMASS "forest height" is an upper-canopy stand height (H100) from a 200 m radar inversion; GEDI RH98 is a lidar energy percentile over a 25 m footprint. Both fit the CF name `canopy_height`, but they are different quantities, so each variable here carries its definition quoted from its product documentation, and relating one to the other is a model, not an identity. The BIOMASS quality layer is a percentage bias (lower is better).

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
