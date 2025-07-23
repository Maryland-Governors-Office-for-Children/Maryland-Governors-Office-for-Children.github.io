import os
import time
import requests
import pandas as pd
import geopandas as gpd
from tqdm import tqdm

# --- Constants ---
# API endpoints for data fetching
FDIC_API_URL = "https://pfabankapi.app.cloud.gov/api/sod"
NCUA_API_URL = "https://mapping.ncua.gov/api/Search/GetSearchLocations"

# Directory to save the output files and read inputs from
OUTPUT_DIR = "input"
FDIC_OUTPUT_PATH = os.path.join(OUTPUT_DIR, "fdic.geojson")
NCUA_OUTPUT_PATH = os.path.join(OUTPUT_DIR, "ncua.geojson")


def _create_output_dir():
    """
    Creates the output directory if it doesn't already exist.
    """
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Created directory: {OUTPUT_DIR}")


def fetch_fdic_data():
    """
    Fetches bank branch data from the FDIC API for the state of Maryland.

    Returns:
        geopandas.GeoDataFrame: A GeoDataFrame containing FDIC branch locations
                                and associated data, or None if an error occurs.
    """
    # Payload for the API request, filtering for 2024 data in Maryland (MD)
    payload = {
        "limit": 10000,
        "offset": 0,
        "filters": 'YEAR:"2024" AND STALPBR:"MD"',
        "sort_by": "BRNUM",
        "sort_order": "ASC",
    }

    try:
        # Send POST request to the FDIC API
        response = requests.post(FDIC_API_URL, json=payload, timeout=60)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        # Parse the JSON response
        data = response.json()
        
        # Check if the 'data' key exists and is a list
        if not data.get("data") or not isinstance(data["data"], list):
            print("FDIC API returned no data or in an unexpected format.")
            return None

        # The actual branch data is in a nested 'data' dictionary. This extracts it.
        records = [item['data'] for item in data['data'] if 'data' in item]

        if not records:
            print("FDIC API response contained no valid records.")
            return None

        # Convert the list of records to a pandas DataFrame
        df = pd.DataFrame(records)

        # Convert the pandas DataFrame to a GeoDataFrame
        # Geometry is created from the longitude and latitude columns
        gdf = gpd.GeoDataFrame(
            df,
            geometry=gpd.points_from_xy(df.SIMS_LONGITUDE, df.SIMS_LATITUDE),
            crs="EPSG:4326",  # WGS84 coordinate reference system
        )
        return gdf

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching FDIC data: {e}")
        return None
    except (KeyError, ValueError, TypeError) as e:
        print(f"Error parsing FDIC API response: {e}")
        return None


def _get_maryland_zip_codes():
    """
    Reads Maryland ZIP codes from a local CSV file (input/zips.csv).
    
    Returns:
        list: A list of unique ZIP code strings for Maryland, or None if an error occurs.
    """
    zip_csv_path = os.path.join(OUTPUT_DIR, "zips.csv")
    try:
        print(f"Reading Maryland ZIP codes from {zip_csv_path}...")
        # Read the local CSV file, ensuring zip codes are treated as strings
        zips_df = pd.read_csv(zip_csv_path, dtype={'zip': str})

        # Check if the 'zip' column exists
        if "zip" not in zips_df.columns:
            print(f"Error: 'zip' column not found in {zip_csv_path}")
            return None

        # Get the unique ZIP codes from the 'zip' column
        unique_zips = zips_df["zip"].dropna().unique().tolist()
        print(f"Found {len(unique_zips)} unique ZIP codes in Maryland.")
        return unique_zips
        
    except FileNotFoundError:
        print(f"Error: The file {zip_csv_path} was not found.")
        print("Please ensure 'input/zips.csv' exists and contains a 'zip' column.")
        return None
    except Exception as e:
        print(f"Failed to read or process Maryland ZIP codes from CSV: {e}")
        return None


def fetch_ncua_data():
    """
    Fetches credit union branch data from the NCUA API for Maryland.
    It first identifies all ZIP codes in Maryland and then queries the NCUA
    API for branches in each of those ZIPs.

    Returns:
        geopandas.GeoDataFrame: A GeoDataFrame containing NCUA branch locations
                                and associated data, or None if an error occurs.
    """
    # Get the list of all ZIP codes in Maryland
    maryland_zips = _get_maryland_zip_codes()
    if not maryland_zips:
        return None

    all_branches = []
    print("Querying NCUA API for branches in each Maryland ZIP code...")
    # Loop through each ZIP code with a progress bar
    for zip_code in tqdm(maryland_zips, desc="NCUA Progress"):
        payload = {
            "searchText": zip_code,
            "rdSearchType": "address",
            "skip": 0,
            "take": 100,  # Assume max 100 branches per ZIP
        }

        try:
            # Send POST request to the NCUA API
            response = requests.post(NCUA_API_URL, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if data.get("list"):
                all_branches.extend(data["list"])
            
            # Be polite to the server by waiting between requests
            time.sleep(1)

        except requests.exceptions.RequestException as e:
            print(f"\nWarning: Could not fetch data for ZIP {zip_code}. Error: {e}")
        except (KeyError, ValueError) as e:
            print(f"\nWarning: Error parsing response for ZIP {zip_code}. Error: {e}")
    
    if not all_branches:
        print("NCUA API returned no branch data for any Maryland ZIP code.")
        return None

    # Convert the list of branch dictionaries to a DataFrame
    df = pd.DataFrame(all_branches)

    # Remove "distance" and "index" columns from df as they're not unique
    df = df.drop(columns=["distance", "index"], errors="ignore")

    # Filter results to ensure state is Maryland and remove duplicates
    df = df[df["state"] == "MD"].drop_duplicates()

    # Convert to a GeoDataFrame
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df.addressLongitude, df.addressLatitude),
        crs="EPSG:4326",
    )
    return gdf


def run():
    """
    Main function to execute the data fetching and saving process.
    """
    print("Starting financial data fetching process...")
    _create_output_dir()

    # --- FDIC Data ---
    print("\nFetching FDIC bank branch data for Maryland...")
    fdic_gdf = fetch_fdic_data()
    if fdic_gdf is not None and not fdic_gdf.empty:
        try:
            fdic_gdf.to_file(FDIC_OUTPUT_PATH, driver='GeoJSON')
            print(f"Successfully saved FDIC data to {FDIC_OUTPUT_PATH}")
        except Exception as e:
            print(f"Error saving FDIC GeoJSON: {e}")
    else:
        print("Failed to fetch or process FDIC data. File not created.")

    # --- NCUA Data ---
    print("\nFetching NCUA credit union branch data for Maryland...")
    ncua_gdf = fetch_ncua_data()
    if ncua_gdf is not None and not ncua_gdf.empty:
        try:
            ncua_gdf.to_file(NCUA_OUTPUT_PATH, driver='GeoJSON')
            print(f"Successfully saved NCUA data to {NCUA_OUTPUT_PATH}")
        except Exception as e:
            print(f"Error saving NCUA GeoJSON: {e}")
    else:
        print("Failed to fetch or process NCUA data. File not created.")
    
    print("\nProcess finished.")


if __name__ == "__main__":
    run()
