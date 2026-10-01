# Snakefile — orchestrates the pipeline end-to-end; each rule executes one jupytext notebook.
#
# 01 needs credentials in the environment (ESA MAAP and NASA Earthdata): see notebooks/01_data_download.py.
#
# Usage:
#   snakemake --cores 1                  # run everything
#   snakemake --cores 1 -n               # dry run

NOTEBOOKS = "notebooks"
DATA = "data"
RESULTS = "results"
FIGURES = "figures"
STORE = "measurements/canopy_height/11"


rule all:
    input:
        f"{FIGURES}/main_result.png",
        f"{RESULTS}/summary.csv",


# ---------- 01: Data download (BIOMASS via ESA MAAP, GEDI via NASA Earthdata) ----------
rule data_download:
    output:
        f"{DATA}/raw/sources.json",
        f"{DATA}/raw/biomass_fh/items.json",
        f"{DATA}/raw/gedi_l2a_beni.parquet",
    log:
        f"{RESULTS}/logs/01_data_download.log",
    shell:
        f"cd {{NOTEBOOKS}} && jupytext --to notebook --execute 01_data_download.py 2>&1 | tee ../{{log}}"


# ---------- 02: All layers on WGS84 HEALPix depth 11, self-describing ----------
rule data_clean:
    input:
        f"{DATA}/raw/sources.json",
        f"{DATA}/raw/biomass_fh/items.json",
        f"{DATA}/raw/gedi_l2a_beni.parquet",
    output:
        directory(f"{DATA}/clean/beni_canopy_height.zarr"),
        f"{DATA}/clean/biomass_products.csv",
    shell:
        f"cd {{NOTEBOOKS}} && jupytext --to notebook --execute 02_data_clean.py"


# ---------- 03: Agreement, calibration model, EBV ----------
rule analysis:
    input:
        f"{DATA}/clean/beni_canopy_height.zarr",
    output:
        f"{RESULTS}/summary.csv",
        f"{RESULTS}/summary.json",
        f"{RESULTS}/calibration_cells.parquet",
        directory(f"{RESULTS}/beni_canopy_height_ebv.zarr"),
    shell:
        f"cd {{NOTEBOOKS}} && jupytext --to notebook --execute 03_analysis.py"


# ---------- 04: Figures ----------
rule figures:
    input:
        f"{RESULTS}/summary.json",
        f"{RESULTS}/beni_canopy_height_ebv.zarr",
    output:
        f"{FIGURES}/main_result.png",
    shell:
        f"cd {{NOTEBOOKS}} && jupytext --to notebook --execute 04_figures.py"
