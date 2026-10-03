# 10 — Dataset (optional)

> Run the pre-flight checklist in `docs/forrt-form-fields.md` § Pre-flight checklist before drafting.
>
> **Scope check:** a Dataset nanopub declares a **FAIR digital object** — data
> that exists at a persistent identifier and that others could reuse. It earns
> its place here because the canopy-height product *is* a contribution of this
> work, not merely an input to it: it is the Essential Biodiversity Variable the
> chain set out to produce. Data merely *consumed* by the study (GEDI L2A) does
> not need its own Dataset nanopub — step 06 already cites it as `usesDataFrom`.

**Form heading:** *"FAIR Dataset — Describe a FAIR Digital Object dataset with metadata including creators, version, license, and access information."*

> **Why this one does reach the constellation.** The template's *project* field
> is a guided choice over project nanopublications, so setting it to the PICO
> question's URI creates a nanopub→nanopub reference. The constellation walk
> follows exactly those, so this dataset attaches to the chain — unlike the
> geographical coverage in `09_geo_coverage.md`, which can only point at a DOI.

## Field-by-field draft

<!-- field: fdo -->
### Dataset Identifier (text input, required)

The persistent identifier of the dataset, full URL form. This is the same
identifier step 06 cites as `usesDataFrom`, so the two records agree on what
the data is.

```
https://doi.org/10.57780/bio-65e97bc
```

<!-- field: label -->
### Dataset Title (text input, required, 3–300 chars)

Name the variable, the place and the sensor — a reader scanning a list should be
able to tell whether this is the data they need without opening it.

```
Canopy height for the Beni lowlands, Bolivia: an Ecosystem Vertical Profile EBV from ESA BIOMASS, validated against GEDI lidar
```

<!-- field: description -->
### Description (long text, required, 10–2000 chars)

What the data is, how it was made, what it was checked against, and what it is
for. Name the EBV class explicitly — that is what makes this discoverable as a
biodiversity variable rather than as a generic raster.

```
Forest canopy height for the lowland forests of the Beni Department, Bolivia, derived from ESA BIOMASS P-band synthetic aperture radar and validated against NASA GEDI spaceborne lidar (GEDI L2A, https://doi.org/10.5067/GEDI/GEDI02_A.003). The product is published as an Essential Biodiversity Variable of the GEO BON class Ecosystem Vertical Profile: canopy height is the vertical structure measurement that class is defined on. The study is question-rooted — it asks how BIOMASS-derived height compares with lidar-derived height in a seasonally flooded, structurally heterogeneous landscape — rather than replicating a prior paper. Skidmore et al. 2021 (https://doi.org/10.1038/s41559-021-01451-x) is the foundation reference for vegetation height as a satellite-observed biodiversity product, and is cited as an authority rather than as a work this dataset confirms or disputes.
```

<!-- field: domain -->
### Subject / Domain (text input, optional)

```
Essential Biodiversity Variables — Ecosystem Vertical Profile (GEO BON)
```

<!-- field: creators -->
### Creators (repeatable, ORCID URLs)

The ORCID the rest of this chain is attributed to. Add co-creators of the data
product if they differ from the chain's author.

```
https://orcid.org/0000-0002-1784-2920
```

<!-- field: project -->
### Project (guided choice, optional — but it is the field that links this into the chain)

Set to the **PICO research question URI published in step 01**, from
`nanopubs/PUBLISHED.md`. This is what attaches the dataset to the constellation;
leave it blank and the dataset publishes fine but floats free of the chain.

```
https://w3id.org/sciencelive/np/RAzN11guB556AYHGiB9B_YMoS8d0TDPL0Jw1tfU4KFNhc
```

<!-- field: version -->
### Version (text input, optional)

The version of the data product this record describes, not of the code. A
nanopub is immutable: if the data is reprocessed, publish a new Dataset nanopub
rather than letting this one silently describe different numbers.

```
{{DATA_VERSION — e.g. 1.0; leave blank if the DOI is already version-specific}}
```

<!-- field: contactEmail -->
### Contact Email (text input, optional)

```
{{CONTACT_EMAIL — the address that will still work in five years, ideally institutional}}
```

<!-- field: publisher -->
### Publisher (ROR, optional)

ROR URL of the organisation that issued the DOI and holds the data.

```
{{PUBLISHER_ROR — https://ror.org/...}}
```

<!-- field: funder -->
### Funder (ROR, optional)

```
{{FUNDER_ROR — https://ror.org/...}}
```

<!-- field: language -->
### Language (text input, optional)

Language of the metadata, not of the data values. Leave blank for a numeric
raster product unless the accompanying documentation is in a specific language.

```

```

<!-- field: fairProfile -->
### FAIR Implementation Profile (text input, optional)

```

```

<!-- field: contributors -->
### Contributors (repeatable, ORCID URLs)

```

```

## After publishing

1. Record the URI in `nanopubs/PUBLISHED.md` under row 10.
2. Re-open the story view for the chain. The dataset should now appear in
   *Nanopublications in this chain*, named by its template rather than dropped.
   If it does not, check that *project* was set to the step 01 URI — that
   reference is the only thing attaching it.
