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

The DOI of the dataset, in bare form — no `https://doi.org/` resolver prefix.
This is the same dataset step 06 cites as `usesDataFrom`.

```
10.57780/bio-65e97bc
```

> **Confirmed: the DOI is minted as a local suffix, not used as the identifier.**
> `fdo` is declared `nt:LocalResource, nt:UriPlaceholder` ("full URI … or short
> suffix"), and generating this template with the bare DOI produces
>
> ```
> <https://w3id.org/sciencelive/np/RA…/10.57780/bio-65e97bc> a fdof:FAIRDigitalObject
> ```
>
> — the dataset is identified by a URI inside this nanopublication, **not** by
> `https://doi.org/10.57780/bio-65e97bc`, which is what step 06 cites as
> `usesDataFrom`. The two records therefore describe two different resources and
> nothing links them.
>
> Entering the full resolver URL is not a workaround: the form validates `fdo`
> against a regex that forbids `:`, so `https://…` is rejected outright. Until
> the template or the form grows a way to say "this DOI *is* the dataset", the
> link between the citation and this record has to be made some other way — a
> CiTO citation pointing at this nanopublication's URI, for instance.

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
### Subject / Domain (autocomplete, optional)

**This field takes a URI from a fixed list, not free text.** The template
declares it `nt:RestrictedChoicePlaceholder` with `nt:possibleValuesFrom`, so
the form is an autocomplete over a controlled vocabulary (AGROVOC, EDAM, NCIT,
OBO…). Pick from the dropdown rather than typing a description.

Beware the failure mode: a value outside the list does not raise an error — the
generated nanopublication comes back with **no assertion graph at all**, silently.
If your preview shows an empty assertion, this field is the first thing to check.

`http://edamontology.org/topic_3050` is EDAM's *Biodiversity*. The nearest
alternatives in the list are `http://aims.fao.org/aos/agrovoc/c_6498`
(*Remote Sensing*), `http://purl.obolibrary.org/obo/NCIT_C16526` (*Ecology*) and
`http://aims.fao.org/aos/agrovoc/c_16129` (*Forest Management*). There is no
"Essential Biodiversity Variables" entry; the EBV framing lives in the
description instead.

```
http://edamontology.org/topic_3050
```

<!-- field: creators -->
### Creators (repeatable, ORCID URLs)

**Not the author of this chain.** The creators are whoever produced the dataset
— the team behind the canopy-height product — which is a different credit from
having published the replication study that uses it. Getting this wrong assigns
someone else's data to you in a signed, permanent record.

If you contributed to the chain but not to the data, you belong in
*Contributors* or nowhere in this nanopub at all; your authorship of the study
is already recorded in steps 01–06.

```
{{CREATOR_ORCIDS — the dataset's own creator(s), one per row}}
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

## Before publishing — check the preview

Generating this template with unfilled optional fields leaks the template's own
placeholder URIs into the assertion, e.g.

```
dc:creator <https://w3id.org/np/RAuVB37yy…/creator> ;
dcat:contactPoint "https://w3id.org/np/RAuVB37yy…/contact"
```

Those are not values, they are the placeholders themselves. Publishing that
would assert a meaningless creator in a signed, permanent record — so either
fill *creators* and *contact email* properly, or confirm the preview does not
carry a `…/creator` or `…/contact` URI before you sign.

## After publishing

1. Record the URI in `nanopubs/PUBLISHED.md` under row 10.
2. Re-open the story view for the chain. The dataset should now appear in
   *Nanopublications in this chain*, named by its template rather than dropped.
   If it does not, check that *project* was set to the step 01 URI — that
   reference is the only thing attaching it.
