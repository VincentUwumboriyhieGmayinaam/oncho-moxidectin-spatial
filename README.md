# Where people miss onchocerciasis treatment: Clustering and persistence of non-participation during ivermectin and moxidectin mass drug administration in Ghana

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24223133.svg)](https://doi.org/10.5281/zenodo.24223133)

Analysis code for the article:

> [FILL: authors]. Where people miss onchocerciasis treatment: Clustering and persistence of non-participation during ivermectin and moxidectin mass drug administration in Ghana. PLOS Neglected Tropical Diseases. [FILL: year, DOI].

The code reproduces every number, table, map and figure in the article. It does **not** contain any survey data or
household coordinates (see [Data access](#data-access)).

## What the study did

Three independent household surveys (400 respondents per round) were carried out in Twifo Atti-Morkwa District,
Ghana, after one ivermectin and two moxidectin mass drug administration (MDA) rounds. Household GPS points were linked
to public river maps. The analysis:

- searches the map for places where more people missed treatment than chance would give (spatial scan);
- checks whether neighbouring communities have similar participation, and whether low communities stay low across
  rounds;
- compares Round 3 participation by distance to larger rivers and by reported black flies;
- tests how well the cluster method behaves when communities differ but are not arranged in a spatial pattern
  (simulation).

## How the code is organised

Each script starts with a header that explains its purpose, inputs, outputs and the methods it uses. Inside the
scripts, every analysis step is a separate block preceded by a comment explaining the method and why it was chosen;
blocks are separated by one blank line. Scripts are numbered in the order they run.

## Repository layout

```
run_all.sh                       runs the whole pipeline
src/01_build_datasets.py         builds the analysis file from the raw survey export, including GPS cleaning
                                 (swapped latitude/longitude, missing decimal points, typing errors)
src/02_prepare_boundaries.py     district boundary, neighbouring districts, 226 settlements, survey community centroids
src/03_clip_hydrorivers.py       HydroRIVERS v1.0 clipped to the district region (UTM 30N, EPSG:32630)
src/04_osm_waterways.py          OpenStreetMap waterways from a Ghana .osm.pbf extract
src/core.py                      shared modelling code: CR2 variance, Bell-McCaffrey df, modified Poisson, standardisation
src/05_analysis.py               distances, exposure summaries, agreement, spatial scan (household and community level),
                                 Moran's I, Getis-Ord Gi*, persistence, exposure-participation models, sensitivity analyses
src/06_scan_validation.py        brute-force check of the scan, type I error and power by simulation, SaTScan input files
src/07_figures.py                Figures 1-4 (maps and plots)
src/apa_helpers.py               table and figure helpers shared with the Paper 3 repository
src/08_results_report.py         Word report with all APA-style tables and figures
docs/codebook.md                 definitions of the variables used
data/README.md                   which data files are needed and how to obtain them
```

## Methods in brief

| Step | Method | Where |
|---|---|---|
| Distance to rivers | Straight-line distance from each household to the nearest river segment, UTM zone 30N | `05_analysis.py` |
| Larger rivers | HydroRIVERS Strahler order >= 3 (Pra and main tributaries) | `03_clip_hydrorivers.py` |
| Clusters (primary) | Kulldorff Bernoulli scan on household locations; circular windows on 226 settlement points; max 25% of respondents; 999 Monte Carlo replicates | `05_analysis.py` |
| Clusters (sensitivity) | Community-level scan; null from 999 permutations of community totals (seed 11) | `05_analysis.py` |
| Scan validation | Independent brute-force enumeration; 500 null and 300 power data sets (beta-binomial, ICC 0.18) | `06_scan_validation.py` |
| Spatial autocorrelation | Moran's I (4 nearest neighbours; 3, 5 and inverse distance as sensitivity), 9,999 permutations; Gi* | `05_analysis.py` |
| Persistence | Spearman correlation of community participation between rounds, Fisher CIs | `05_analysis.py` |
| Exposure-participation | Modified Poisson regression, CR2 variance, Bell-McCaffrey df (20 communities); spline of log distance with marginal standardisation | `05_analysis.py` |

`06_scan_validation.py` also writes SaTScan case, population and coordinate files so the primary scan can be re-run in
SaTScan (free from satscan.org). These files contain coordinates and are written only to `outputs/`, which is never
committed.

## Public input data

| Data | Source | File expected |
|---|---|---|
| HydroRIVERS v1.0, Africa | Lehner & Grill (2013), https://www.hydrosheds.org/products/hydrorivers | `data/hydrorivers/HydroRIVERS_v10_af.shp` |
| OpenStreetMap Ghana extract (3 November 2026) | Geofabrik, https://download.geofabrik.de/africa/ghana.html | `data/ghana-latest.osm.pbf` |
| District boundaries and settlements | [FILL: source, e.g. Ghana Statistical Service] | `data/district/New_District.shp`, `Community.shp` |

## How to reproduce

Requirements: Python 3.13 and the packages in `requirements.txt` (exact versions used for the article).

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# put the files listed in data/README.md in data/
bash run_all.sh
```

On Windows without bash, run the `python` lines in `run_all.sh` one by one from the repository folder. The scan
validation (500 + 900 simulated data sets) is the slowest step. Random seeds are fixed.

## Data access

Household coordinates and community names identify respondents and are not shared. De-identified survey files can be
requested from the corresponding author; see `data/README.md`. Maps show community centroids only, labelled C01-C22.

## Citation and licence

Please cite the article and this repository (`CITATION.cff`). Version used for the submitted manuscript: v1.1.0, doi: [10.5281/zenodo.24223133](https://doi.org/10.5281/zenodo.24223133). Code is released under the MIT licence. HydroRIVERS and
OpenStreetMap data keep their own licences (HydroSHEDS licence; ODbL). The study was approved by [FILL: ethics
committee and approval number].
