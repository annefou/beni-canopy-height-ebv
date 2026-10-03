# 09 — Geographical coverage (optional)

> Run the pre-flight checklist in `docs/forrt-form-fields.md` § Pre-flight checklist before drafting. Read `docs/geo-coverage.md` first.
>
> **When to draft this.** Only when the paper's findings have a **specific geographic
> scope** — a study area, region, country, transect, or named site (typical for
> earth-observation, biodiversity, ecology, epidemiology work). A non-spatial paper
> (e.g. a lab cognition study with no study area) has **no** geographic coverage —
> delete this draft and skip the step. Do not invent a location to fill the form.
>
> **What it documents.** The geographic coverage of the **original paper** (subject =
> the paper DOI), backed by a **verbatim quotation** from the paper that names the
> area. Grounded, Record-side — place name and quote from the PDF; geometry resolved
> by the form's map/geocoder, never hand-written. Publishes with the platform's
> existing **"Document geographical coverage"** template; discoverable via GeoSPARQL.

## More than one location

A paper can cover **several areas**. Handle it one of two ways:

- **Distinct study sites** (separately meaningful — e.g. two estuaries compared, three
  field sites): publish **one coverage nanopub per site**, so each is individually
  named, quoted, and spatially searchable. Duplicate the *per-location block* below,
  once per site — each with its **own** area name, **own** verbatim quote, and own
  geometry. This is the atomic default.
- **One pooled coverage** (regions the study treats as a single combined extent —
  e.g. "North America, the EU and Australia" pooled in one analysis): publish **one**
  nanopub. In the form's location search, add each place in turn — it merges them into
  a single `GEOMETRYCOLLECTION` under one combined label. Use one block below, list
  the places in the label, and quote the sentence that names them together.

If unsure, prefer separate nanopubs — atomic coverage is easier to search and cite.

## Shared field

<!-- field: paper -->
### Cited DOI (text input, required — same for every location)

The **original paper's** DOI (bare, starting `10.` — the form prepends `https://doi.org/`). Same DOI as the Quote (step 01) / CiTO (step 06). Read it from `CITATION.cff` `references:`; do not recall it.

> **This study:** question-rooted, and its reference paper (Skidmore et al. 2021) is global with no study area. The coverage is therefore anchored on this study's own release, the Zenodo **version DOI** of v0.1.0 (recorded in `CITATION.cff` `identifiers:`), which deposits the source quoted below.

```
10.5281/zenodo.23120435
```

---

## Per-location block — duplicate this whole section once per distinct site

> Publish one "Document geographical coverage" nanopub per block below. For a single
> location, keep one block. For a pooled multi-region coverage, keep one block and add
> each place in the form's location search (it builds the GeometryCollection).

### Location A

<!-- field: quoteType -->
**Quote type** (radio: whole | ends, required) — `whole` if under 500 characters (usual); `ends` only for a long start/end passage.

```
whole
```

<!-- field: quotation -->
**Quoted Text** (textarea, required) — the **verbatim** sentence from the paper naming *this* area. Character-for-character from the PDF; never paraphrase. Each location needs its own quote.

```
Region: the Beni lowlands, Bolivia (bbox lon −67.5 to −64.5, lat −15.5 to −12.5), as in `beni-fire-biomass-healpix` and the ESA Frontiers `beni-pipeline`.
```

<!-- field: quotation-end -->
**Quoted Text End** (textarea, optional — only if quote type = ends). Leave blank for `whole`.

```

```

<!-- field: location -->
**Short ID for location** (text input, required) — slug for the URI suffix (lowercase, hyphenated), unique per location. E.g. `sado-estuary`, `westerschelde`, `amazon-basin`.

```
beni-lowlands-bolivia
```

<!-- field: location-label -->
**Area name** (text input, required) — human-readable name as the paper frames it. E.g. `Sado Estuary, Portugal`. Typing this into the form's **location search** geocodes it and fills the geometry.

```
Beni lowlands, Bolivia
```

<!-- field: geometry -->
**Short ID for geometry** (text input, optional) — URI suffix for the geometry node; `coverage` is fine.

```
coverage
```

<!-- field: wkt -->
**Geometry as Well-known Text (WKT)** (map / text, resolved in the form) — **Do NOT hand-write coordinates.** The form geocodes the area name to a polygon, or you draw it on the map. Only paste explicit `POINT(...)` / `POLYGON((...))` if the paper **states coordinates verbatim** — copied exactly. A hallucinated bounding box is a fabricated datum; leave blank otherwise.

```
POLYGON((-67.5 -15.5, -64.5 -15.5, -64.5 -12.5, -67.5 -12.5, -67.5 -15.5))
```

<!-- field: comment -->
**Comment** (textarea, required) — one or two sentences on **how the quoted text supports** this being the coverage. Grounded in the paper, no new claims.

```
The quoted sentence, from notebooks/01_data_download.py in the v0.1.0 deposit, states the study region and its bounding box; the geometry is that bounding box, with the coordinates copied as stated. All results of the study are for this box.
```

## Publication note

Each location block is a **standalone** nanopub, not one of the six FORRT chain steps.
Publish each via the platform's **"Document geographical coverage"** template (Create →
that template). After publishing, paste each resulting URI into `nanopubs/PUBLISHED.md`
under a "Geographical coverage" row (one row per location) so `/verify-chain` and the
story page can find them.
