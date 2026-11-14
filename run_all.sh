#!/usr/bin/env bash
# Reproduces all results, tables and figures for Paper 5.
# Usage: bash run_all.sh            (expects the files listed in data/README.md)
#        bash run_all.sh --build <survey.xlsx> <variable_audit.xlsx>   (rebuild the analysis file from the raw survey export first)
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p outputs/gis outputs/figures
if [[ "${1:-}" == "--build" ]]; then python -I src/01_build_datasets.py "$2" "$3" data; fi
python -I src/02_prepare_boundaries.py data/district data/paper5_spatial.csv outputs/gis
python -I src/03_clip_hydrorivers.py data/hydrorivers/HydroRIVERS_v10_af.shp outputs/gis/tam_district.gpkg outputs/gis/rivers_tam_region.gpkg
python -I src/04_osm_waterways.py data/ghana-latest.osm.pbf outputs/gis/tam_district.gpkg outputs/gis/osm_waterways.gpkg
python -I src/05_analysis.py data/paper5_spatial.csv outputs/gis outputs
python -I src/06_scan_validation.py data/paper5_spatial.csv outputs/p5_results.pkl outputs/scan_validation
python -I src/07_figures.py outputs/p5_results.pkl outputs/gis data/district/New_District.shp outputs/figures
python -I src/08_results_report.py outputs/p5_results.pkl outputs/figures "outputs/Paper 5 results - tables and figures.docx" src/apa_helpers.py
echo "Done. Results are in outputs/."
