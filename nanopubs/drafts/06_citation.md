# 06 — CiTO Citation

> Run the pre-flight checklist in `docs/forrt-form-fields.md` § Pre-flight checklist before drafting.

**Description:** *"Declare citations between papers or other works, using Citation Typing Ontology"*

## Field-by-field draft

<!-- field: work -->
### Identifier for the citing creative work (text input, required)

URI of the Outcome published in step 05. Pull from `nanopubs/PUBLISHED.md`.

```
«URI of step 05 (FORRT Replication Outcome)»
```

### List citations (repeatable group, required ≥1)

#### Citation 1 — back to the original paper

##### Citation Type (dropdown)

Choose based on the Outcome's validation status:

- Validated → `confirms`
- PartiallySupported → `qualifies`
- Contradicted → `disputes`

For question-rooted chains where there is no original paper to confirm/dispute, use `usesMethodIn` or `citesAsAuthority` for the methodology paper(s).

> **Note:** `replicates` is NOT in the Science Live dropdown (despite existing in upstream CiTO). When citing a notebook/tutorial that was directly reused, use **`credits`** instead.

Question-rooted chain: Skidmore et al. 2021 is not confirmed or qualified here; it is the authority for vegetation height as a satellite biodiversity product (Table 2, no. 14). **Set this by hand in the wizard:** `scripts/build_chain_draft.py` derives the type from the validation status and would pre-fill `qualifies`.

```
cites as authority
```

##### DOI or other URL of the cited work (text input)

```
https://doi.org/10.1038/s41559-021-01451-x
```

#### Additional citations (optional)

If the Outcome cites methods papers, related replications, or upstream tools, add them here.

- Type: cites as authority → URL: https://doi.org/10.1016/j.tree.2020.03.006 (Valbuena et al. 2020: definition of ecosystem height, cover and structural complexity used for the EBV components)
- Type: cites as authority → URL: https://doi.org/10.1126/science.1229931 (Pereira et al. 2013: Essential Biodiversity Variables)
- Type: uses data from → URL: https://doi.org/10.57780/bio-65e97bc (ESA BIOMASS Level 2A)
- Type: uses data from → URL: https://doi.org/10.5067/GEDI/GEDI02_A.003 (GEDI L2A V003)

## Publication note

After publishing, paste the resulting URI into `nanopubs/PUBLISHED.md` step 06.

This completes the six-step FORRT chain. Optional next layers:

- **Research Software** (`drafts/07_research_software.md`) — if the repo *produces* a reusable software artefact.
- **Research Synthesis** (`drafts/08_synthesis.md`) — if this chain is one of several testing facets of a shared property.
