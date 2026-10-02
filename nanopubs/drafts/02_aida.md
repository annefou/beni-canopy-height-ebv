# 02 — AIDA Sentence

> Run the pre-flight checklist in `docs/forrt-form-fields.md` § Pre-flight checklist before drafting.

**Form heading:** *"AIDA Sentence — Make structured scientific claims following the AIDA model"*

## Field-by-field draft

<!-- field: aida -->
### AIDA sentence (text input, required)

Atomic, Independent, Declarative, Absolute. One empirical finding. Must end with a full stop.

> _If your draft AIDA contains "and" linking two distinct findings, split into two AIDA nanopubs._

```
Forest canopy height estimated by the ESA BIOMASS radar mission is lower than forest canopy height measured by spaceborne lidar in the lowland forests of the Bolivian Beni.
```

<!-- field: topic -->
### Select related topics/tags (search/select, optional)

Predefined topic vocabulary — list the labels you intend to pick from the dropdown.

```
forest canopy (Q105427924)
remote sensing (Q199687)
lidar (Q504027)
synthetic aperture radar (Q740686)
```

<!-- field: project -->
### Relates to this nanopublication (search/select, required)

URI of the nanopub the AIDA derives from.

- For paper-rooted chains: the Quote-with-comment URI (from step 01).
- For question-rooted chains: the PICO or PCC URI (from step 01).

Pull the URI from `nanopubs/PUBLISHED.md`.

```
«URI of step 01 (PICO Research Question)»
```

<!-- field: dataset -->
### Supported by datasets (text input, optional)

DOIs/URLs of datasets that ground the AIDA claim.

- DOI 1: https://doi.org/10.57780/bio-65e97bc (ESA BIOMASS Level 2A)
- DOI 2: https://doi.org/10.5067/GEDI/GEDI02_A.003 (GEDI L2A V003)
- DOI 3: https://doi.org/10.5281/zenodo.7254221 (ESA WorldCover 10 m 2021 v200, forest focus group)

<!-- field: publication -->
### Supported by other publications (text input, optional)

DOIs/URLs of publications that support the AIDA claim — e.g. peer-reviewed methods papers, or the original paper if not already cited via the Quote.

- _DOI 1: ___
- _DOI 2: ___

> **Known platform bug (2026-04-26):** if both *Supported by datasets* AND *Supported by other publications* are populated and publishing fails, fall back to publishing this AIDA via Nanodash. The URI namespace becomes `https://w3id.org/np/...` (still valid and citable).

## Publication note

After publishing, paste the resulting URI into `nanopubs/PUBLISHED.md` step 02.
