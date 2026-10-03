# 09 — Document geographical coverage (optional, spatial papers)

> Run the pre-flight checklist in `docs/forrt-form-fields.md` § Pre-flight checklist before drafting.
>
> **Scope check:** this nanopub states *where on Earth* a work applies. It earns
> its place when the claim is bounded by geography — as this chain's is: canopy
> height in the **Beni lowlands of Bolivia**, not canopy height in general. It
> also puts the work on the platform's **Geographic** browse tab, which reads
> `dct:spatial`; without it, a spatially-bounded study is invisible on the map.

**Form heading:** *"Geographical Coverage — Document the geographical area a paper or dataset is about."*

> **Known limitation — this nanopub will not appear in the constellation.**
> The template's *paper* field is a URI placeholder fixed to the prefix
> `https://doi.org/`, so a geographical coverage attaches to a **DOI**, never to
> a nanopublication URI. The constellation walk follows nanopub→nanopub
> references (`npa:refersToNanopub`), so it has no edge to follow here and the
> coverage will not show as a step of this chain. It still publishes correctly,
> is independently citable, and still reaches the Geographic browse tab. If the
> coverage must also appear in the chain, cite its nanopub URI from a CiTO
> citation (e.g. `citesAsRelated`) in a later step.

## Field-by-field draft

<!-- field: paper -->
### DOI of the paper (text input, required, prefix `https://doi.org/`)

This chain is question-rooted: there is no original paper. The work this
coverage describes is the dataset itself, so use the dataset DOI — the same one
step 06 cites as `usesDataFrom` and `10_dataset.md` declares.

```
https://doi.org/10.57780/bio-65e97bc
```

<!-- field: quoteType -->
### Quote type (dropdown, required)

The sentence below states the study area, so it is a plain quotation of the
work's own scope statement.

```
quotation
```

<!-- field: quotation -->
### Quotation (text input, required)

A sentence from the work that states the area the result applies to. Replace
with the exact wording in the dataset description or the paper if one is written
later — the quotation should be verbatim, not paraphrased.

```
Canopy height is estimated for the lowland forests of the Beni Department, Bolivia, from ESA BIOMASS P-band radar and validated against NASA GEDI spaceborne lidar.
```

<!-- field: location -->
### Short ID for the geographical location (text input, required)

Used as the URI suffix for the location resource. Lowercase, hyphenated.

```
beni-lowlands-bolivia
```

<!-- field: location-label -->
### Location label (text input, required)

Human-readable name, as a reader would recognise it on a map.

```
Beni lowlands, Bolivia
```

<!-- field: wkt -->
### Well-Known Text geometry (long text, optional — but it is what enables spatial queries)

**Approximate, department-level extent — replace before publishing.** The
polygon below is the bounding extent of the Beni Department, not the analysis
footprint. Use the actual extent of the BIOMASS/GEDI comparison (the bounds of
the raster tiles or the AOI shapefile used in the notebook), so the map claims
exactly the area the result covers and no more.

Coordinate order is `longitude latitude`, and the ring must close (first pair
repeated last).

```
POLYGON((-69.5 -15.5, -62.0 -15.5, -62.0 -10.0, -69.5 -10.0, -69.5 -15.5))
```

<!-- field: bbox -->
### Bounding box as WKT POLYGON (long text, optional)

Leave blank when the `wkt` field above already carries the geometry — filling
both states the same thing twice, and the two can drift apart when one is
later corrected.

```

```

<!-- field: comment -->
### Comment (text input, required)

Why this area, in the reader's terms — what makes the extent meaningful rather
than incidental.

```
The Beni lowlands are seasonally flooded tropical forest and savanna mosaic, a structurally heterogeneous landscape where P-band radar and lidar canopy-height retrievals are expected to diverge most. The comparison is bounded to this area; it does not generalise to closed-canopy Amazonian forest without further validation.
```

## After publishing

Record the URI in `nanopubs/PUBLISHED.md` under row 09, then check the work
appears on the platform's **Geographic** tab by searching for a term from the
quotation.
