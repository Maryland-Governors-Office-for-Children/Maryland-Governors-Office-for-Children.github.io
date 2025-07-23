# ENOUGH-Resource-Map
Data pipeline for creating and updating the ENOUGH Resource map geojson

## Overview
This repository contains a data pipeline for aggregating, cleaning, and transforming resource data into GeoJSON files for the ENOUGH Resource Map. The output is used to power a web-based map visualization.

## Setup

### 1. Create and activate a virtual environment (Windows)
Open a terminal in the repository root and run:

```
python -m venv venv
.\venv\Scripts\activate
```

### 2. Install dependencies

```
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy the `.env-example` file to `.env` and add your registered data.gov API key:

```
copy .env-example .env  # On Windows
# or
cp .env-example .env    # On Mac/Linux
```

Edit `.env` and set your data.gov API key (required for FDIC data downloads).

## Running the Pipeline

To run the main data pipeline and generate updated GeoJSON files:

```
python pipeline/main.py
```

## Modules Overview

When you run `python pipeline/main.py`, the following steps occur:

- **osm.py**: Extracts resource locations from OpenStreetMap.
  1. Downloads locations for resource types (grocery, laundry, home repair, auto repair, pharmacy, barber/beauty, medical) using the Overpass API.
  2. Standardizes and saves resource points as `input/resources.csv`.

- **financial.py**: Gathers financial institution data for Maryland.
  1. Downloads bank branch data from the FDIC API and credit union data from the NCUA API (using ZIP codes from `input/zips.csv`).
  2. Cleans and standardizes both datasets, saving as `input/fdic.geojson` and `input/ncua.geojson`.

- **maryland_excel.py**: Downloads and processes Maryland Excels childcare provider data.
  1. Fetches provider data for all counties.
  2. Maps accreditation/achievement codes to readable names.
  3. Outputs standardized provider data as `input/maryland_childcare_data.csv` and `input/childcare.geojson`.

- **combine_data.py**: Combines all data sources and generates outputs for the map.
  1. Downloads and caches grantee tract boundaries from an ArcGIS server.
  2. Loads and processes all resource points (from OSM, financial, and childcare data).
  3. Aggregates, standardizes, and spatially joins points to tracts and grantee areas.
  4. Outputs:
     - CSV of points in grantee tracts (`html/assets/grantee_points.csv`)
     - Separate GeoJSONs for each resource type (`html/assets/*.geojson`)
     - GeoJSON of grantee tracts (`html/assets/grantees.geojson`)

- Input data is located in the `input/` directory. Outputs are written to `html/assets/`.

## Previewing the Map

To preview the generated map and data locally, serve the `html` folder with a simple HTTP server:

```
cd html
python -m http.server
```

Then open your browser to [http://localhost:8000](http://localhost:8000) to view the map.

## Notes
- Input data sources are in `input/`.
- Output GeoJSON and CSV files are in `html/assets/`.
- The web map is in `html/index.html` and loads data from the `assets` folder.
