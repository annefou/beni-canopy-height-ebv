# 05 — FORRT Replication Outcome

> Run the pre-flight checklist in `docs/forrt-form-fields.md` § Pre-flight checklist before drafting.
>
> **Verify the actual numerical results first** by reading `results/` and `notebooks/03_analysis.py`. Don't quote numbers from memory. See `docs/verify-before-drafting.md`.

## Field-by-field draft

<!-- field: outcome -->
### Short URI suffix for outcome ID (text input, required)

Slug. Use kebab-case.

```
beni-biomass-gedi-forest-height-outcome
```

<!-- field: label -->
### Plain-text label for the outcome (text input, required)

Descriptive title.

```
ESA BIOMASS forest height is lower than GEDI lidar canopy height in most Beni lowland forest, but not in low canopies
```

<!-- field: study -->
### Choose study (search/select, required)

URI of the Replication Study published in step 04. Pull from `nanopubs/PUBLISHED.md`.

```
«URI of step 04 (FORRT Replication Study)»
```

<!-- field: repo -->
### Repository URL (text input, required)

Use the Zenodo **version DOI** URL for the release the results came from — not a
bare branch URL, and not the concept DOI.

> **Why not the bare repo URL.** `https://github.com/ORG/REPO` names a *moving
> branch*. This Outcome asserts "this code produced this number", in a signed,
> immutable record. A branch URL means that assertion points at whatever `main`
> happens to be years from now — code that may never have produced the number
> above. A concept DOI has the same flaw: it resolves to the latest version.
> The version DOI pins the exact release. `docs/chain-decision-tree.md` § Anchor
> ranks the options: SWHID > Zenodo DOI > repo URL > Wayback.
>
> Both DOIs and the SWHID are in `CITATION.cff` under `identifiers:`, recorded
> automatically at release by `.github/workflows/release-identifiers.yml`. Take
> the one described as *"Version DOI"*.

```
https://doi.org/{{ZENODO_VERSION_DOI}}
```

<!-- field: date -->
### Choose completion date (text input, required)

```
2026-10-02
```

<!-- field: validationStatus -->
### Choose validation status (dropdown, required)


This dropdown maps to the CiTO intention in step 06: Validated → `confirms`, PartiallySupported → `qualifies`, Contradicted → `disputes`.

- [ ] contradicted
- [ ] inconclusive
- [ ] not tested
- [x] partially supported
- [ ] validated

<!-- field: confidenceLevel -->
### Choose confidence level (dropdown, required)

_Vocabulary not yet captured._

```

```

- [ ] high - Strong evidence, mostly agrees with original
- [ ] low - Limited evidence, significant disagreement
- [x] moderate - Adequate evidence, partial agreement
- [ ] very high - Extensive evidence, high agreement with original
- [ ] very low - Minimal evidence, major disagreement

<!-- field: conclusion -->
### Describe the overall conclusion about the original claim (textarea, required)

Substantive interpretation. Headline comparison: replication's number vs the paper's number, sign + significance.

```
Partially supported. Across Beni lowland forest, ESA BIOMASS forest height is lower than GEDI lidar canopy height on average (mean difference -3.0 m, 95 percent block-bootstrap interval -4.4 to -1.1 m) and in 78 percent of forest cells, so the claim holds for most of the forest. It does not hold for low canopies: where GEDI canopy height is lowest (median 10.4 m), BIOMASS is on average 2.1 m higher. BIOMASS compresses the height range: the fitted relation crosses the 1:1 line near 24 m of BIOMASS height. The two heights rank forests only moderately consistently. BIOMASS forest height in its first year is therefore usable for the EBV Ecosystem Vertical Profile only with a stated uncertainty of several metres.
```

<!-- field: evidence -->
### Describe the evidence that supports your conclusion (textarea, required)

Numerical results, test statistics, model coefficients. Read directly from `results/`.

```
Comparison on 1900 forest cells (HEALPix depth 11, WorldCover tree cover at least 50 percent, at least 5 GEDI footprints, at most 5 percent burned in 2024). BIOMASS minus GEDI RH98: mean -3.03 m (95 percent spatial block-bootstrap interval -4.39 to -1.06 m), median -3.83 m, root-mean-square difference 7.18 m; BIOMASS lower in 77.7 percent of cells. Spearman rank correlation 0.58, Pearson 0.52. By thirds of GEDI height (medians 10.4, 19.5, 25.6 m): mean difference +2.1, -4.6, -6.6 m; BIOMASS lower in 48, 87, 97 percent of cells. Linear relation GEDI = 8.61 + 0.645 x BIOMASS, in-sample R2 0.27, cross-validated error 6.59 m (5-fold, 42 spatial blocks). Checks: night-time footprints only, mean difference -2.91 m and Spearman 0.58 (1832 cells); passes combined without the bias weight, mean difference -3.35 m and Spearman 0.59; disagreement against the BIOMASS bias index, Spearman 0.15. Results: results/summary.json.
```

<!-- field: limitations -->
### Describe what limits the conclusions of the study (textarea, optional)

Honest caveats. If the result is partial or contradicted, say so plainly. Don't overclaim.

```
One region and one BIOMASS season (April to August 2026, Level-2A, processors 4.4.4 and 4.4.5 mixed during reprocessing); the products are early and may change. GEDI footprints span 2019 to 2025, so the two heights are years apart; cells burned in 2024 are excluded but later disturbance is not. GEDI RH98 is a lidar energy percentile over 25 m footprints and BIOMASS forest height is an upper-canopy stand height (H100) from radar at 200 m, so part of the difference is definitional; GEDI is itself a satellite product, and no open field-plot heights exist in the region for an independent check. BIOMASS also reports non-zero heights over grassland, and one of 18 products was excluded for reporting about 30 m over grassland. The breakdown by thirds of GEDI height is affected by regression to the mean. The forest focus group uses a 50 percent tree-cover threshold that is our choice.
```

## Publication note

After publishing, paste the resulting URI into `nanopubs/PUBLISHED.md` step 05.
