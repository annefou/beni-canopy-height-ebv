# 04 — FORRT Replication Study

> Run the pre-flight checklist in `docs/forrt-form-fields.md` § Pre-flight checklist before drafting.
>
> **Verify code first:** read the actual reproduction script in `notebooks/03_analysis.py` before writing the methodology field. See `docs/verify-before-drafting.md`.

## Field-by-field draft

<!-- field: study -->
### Short URI suffix for study ID (text input, required)

Slug. Use kebab-case.

```
beni-biomass-gedi-forest-height-study
```

<!-- field: label -->
### Label/name of replication study (text input, required)

Human-readable title.

```
ESA BIOMASS forest height against GEDI lidar canopy height in Beni lowland forests, as input to the EBV Ecosystem Vertical Profile
```

<!-- field: type -->
### Choose the study type (dropdown, required)

- [x] Replication Study - replication with different methodology or conditions
- [ ] Reproduction/Replication Study - study that is both, reproduction and replication
- [ ] Reproduction Study - direct reproduction: same methodology, same tools

<!-- field: claim -->
### Choose FORRT claim (search/select, required)

URI of the Claim published in step 03. Pull from `nanopubs/PUBLISHED.md`.

```
«URI of step 03 (FORRT Claim)»
```

<!-- field: scope -->
### Describe what part of the claim is reproduced/replicated. (textarea, required)

The **scope** of the claim being tested. Which aspect, what's in/out of scope. NOT methodology. NOT results. See `docs/pico-study-outcome-levels.md`.

```
The claim is tested for forest canopy height only, in the lowland forests of the Beni savanna-forest mosaic in Bolivia (longitude 67.5 to 64.5 W, latitude 15.5 to 12.5 S). In scope: the systematic difference, the agreement and the rank consistency between ESA BIOMASS forest height from its first year of operations (2026) and GEDI lidar canopy height, on forest only. Out of scope: grassland and savanna, other regions, biomass (not height), the BIOMASS tomographic and Level-2B products, and field measurements, for which no open data exist in the region.
```

<!-- field: methodology -->
### Describe how the claim is reproduced/replicated. (textarea, required)

The **method** in plain prose. Read `notebooks/03_analysis.py` and any config files first. NOT exact numerical results.

```
All layers are placed on one equal-area grid, HEALPix NESTED on the WGS84 ellipsoid at depth 11 (cells of about 3.2 km). The forest focus group is ESA WorldCover 2021 tree cover: a cell, a BIOMASS pixel or a GEDI footprint counts as forest when its 100 m block is at least half tree cover. BIOMASS: Level-2A forest height (described by ESA as upper canopy height, H100) from the ESA MAAP archive; only forest pixels enter a cell's mean; repeat passes are combined per cell with ESA's inverse-bias weights, 1/(0.01 + bias), times pixel count; a product is excluded when its median height on non-forest pixels exceeds 20 m. GEDI: Level-2A version 3 relative height RH98 from full-power beams, l2a_quality_flag_rel3 = 1 and degrade_flag = 0, subset to the region with NASA Harmony; the cell value is the median over its forest footprints. Comparison cells need both heights, at least 5 GEDI footprints and no more than 5 percent of their burnable area burned in 2024 (ESA Fire_cci), since GEDI (2019-2025) predates BIOMASS. Agreement is measured by mean difference, root-mean-square difference and Spearman rank correlation; a linear relation of GEDI on BIOMASS height is evaluated by 5-fold spatial block cross-validation with blocks of about 51 km. Checks: night-time GEDI footprints only; passes combined without the bias weight; disagreement against the BIOMASS bias index. Code: notebooks/02_data_clean.py and notebooks/03_analysis.py.
```

<!-- field: deviation -->
### Describe any deviations from original methodology. (textarea, optional)

What's different from the original method. Verify against the actual code, don't guess.

```
No original methodology exists: this is a question-rooted study, not a replication of a published analysis. Two choices made during the study are recorded because they change the result: BIOMASS heights were first averaged over whole cells, which mixed grassland into forest cells, and were then restricted to forest pixels; and a first product-exclusion rule (median bias index below 1 percent) also removed a plausible pass, so it was replaced by the non-forest height rule. GEDI version 3 is used instead of version 2 because NASA Harmony serves version 3, and its quality flags are defined differently.
```

<!-- field: keyword -->
### Search keywords (Wikidata) (search/select, optional)

Provide labels (not QIDs) — the Wikidata search picks up labels.

```
forest canopy (Q105427924)
remote sensing (Q199687)
lidar (Q504027)
synthetic aperture radar (Q740686)
HEALPix (Q5629401)
```

<!-- field: discipline -->
### Search discipline (Wikidata) (search/select, optional)

Provide labels.

```
forest ecology (Q2249329)
```

## Publication note

After publishing, paste the resulting URI into `nanopubs/PUBLISHED.md` step 04.
