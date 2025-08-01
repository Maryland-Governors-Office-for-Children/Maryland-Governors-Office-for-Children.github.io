import pandas as pd
import geopandas as gpd
import requests
import os
from pathlib import Path

def run(force_refresh_grantees: bool = False):
    """
    Main function to execute the data processing and combination pipeline.

    Args:
        force_refresh_grantees (bool): If True, redownloads grantee data from the
                                       ArcGIS server instead of using the local cache.
                                       Defaults to False.
    """
    # Define constants for URLs and file paths
    GRANTEE_URL = "https://services.arcgis.com/njFNhDsUCentVYJW/arcgis/rest/services/Grantees_20250623/FeatureServer/0/query?where=1%3D1&outFields=*&f=geojson"
    INPUT_DIR = Path("input")
    OUTPUT_DIR = Path("docs/resource_map/assets")
    GRANTEE_CACHE_PATH = INPUT_DIR / "grantees_raw.geojson"

    # Create directories if they don't exist
    INPUT_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Fetch grantee data, using cache if available
    grantees_gdf = None
    if not force_refresh_grantees and GRANTEE_CACHE_PATH.exists():
        print("Loading grantee data from local cache...")
        try:
            grantees_gdf = gpd.read_file(GRANTEE_CACHE_PATH)
        except Exception as e:
            print(f"Could not read cached file: {e}. Forcing refresh.")
            force_refresh_grantees = True
    
    if force_refresh_grantees or grantees_gdf is None:
        print("Fetching grantee data from ArcGIS Server...")
        try:
            response = requests.get(GRANTEE_URL)
            response.raise_for_status()  # Raise an HTTPError for bad responses
            
            # Save the raw geojson to the cache file
            GRANTEE_CACHE_PATH.write_text(response.text)
            print(f"Cached grantee data to {GRANTEE_CACHE_PATH}")

            # Load the GeoDataFrame from the newly downloaded file
            grantees_gdf = gpd.read_file(GRANTEE_CACHE_PATH)
        except requests.exceptions.RequestException as e:
            print(f"Fatal: Failed to download grantee data: {e}")
            if GRANTEE_CACHE_PATH.exists():
                print("Using stale cache file as a fallback.")
                grantees_gdf = gpd.read_file(GRANTEE_CACHE_PATH)
            else:
                print("No cache available. Cannot proceed.")
                return

    print("Processing grantee data...")
    grantees_gdf = grantees_gdf.to_crs(epsg=4326)

    # Aggregate organization names for unique geometries
    unique_geometry = grantees_gdf.drop_duplicates(subset="GEOID20")[["GEOID20", "geometry"]]
    grantee_data = grantees_gdf.groupby("GEOID20").agg(
        ORGANIZATION_NAME=("ORGANIZATION_NAME", lambda x: "; ".join(x.dropna().unique())),
        GOC_TRACK_TYPE=("GOC_TRACK_TYPE", "first")
    ).reset_index()

    grantees_processed = unique_geometry.merge(grantee_data, on="GEOID20")
    grantees = grantees_processed[grantees_processed["GOC_TRACK_TYPE"].notna() & (grantees_processed["GOC_TRACK_TYPE"] != "")]

    print("Loading and processing resource points...")
    # 2. Load base resource points
    points_df = pd.read_csv(INPUT_DIR / "resources.csv")
    points_gdf = gpd.GeoDataFrame(
        points_df,
        geometry=gpd.points_from_xy(points_df.lng, points_df.lat),
        crs="EPSG:4326"
    )

    # 3. Process and integrate financial data
    print("Processing financial data (FDIC & NCUA)...")
    # FDIC Banks
    fdic_gdf = gpd.read_file(INPUT_DIR / "fdic.geojson")
    fdic_gdf = fdic_gdf.rename(columns={"NAMEFULL": "name"})
    fdic_gdf["tag"] = "bank"
    fdic_gdf["type"] = "financial"
    
    # NCUA Credit Unions
    ncua_gdf = gpd.read_file(INPUT_DIR / "ncua.geojson")
    ncua_gdf = ncua_gdf.rename(columns={"creditUnionName": "name"})
    ncua_gdf["tag"] = "credit_union"
    ncua_gdf["type"] = "financial"
    
    # Combine PALS booleans into a single field
    ncua_gdf["payday_alternative_loans"] = ncua_gdf["palS_I"] | ncua_gdf["palS_II"]
    
    # Define boolean fields to keep from NCUA data
    ncua_boolean_fields = [
        "isMainOffice", "isMdi", "bilingual_Services", "credit_Builder", 
        "financial_Counseling", "first_Time_Homebuyer_Program", "inSchoolBranch",
        "low_cost_wire_transfers", "no_Cost_Tax_Preparation", 
        "no_Cost_Share_Drafts", "payday_alternative_loans"
    ]
    
    financial_gdf = pd.concat([
        fdic_gdf[["name", "type", "tag", "geometry"]],
        ncua_gdf[["name", "type", "tag", "geometry"] + ncua_boolean_fields]
    ], ignore_index=True)

    # 4. Process and integrate childcare data
    print("Processing childcare data...")
    childcare_gdf = gpd.read_file(INPUT_DIR / "childcare.geojson")
    childcare_gdf["tag"] = childcare_gdf["tag_label"].str.lower().str.replace(" ", "_")
    childcare_gdf["type"] = "childcare"
    # Keep the 'quality' field as requested
    childcare_gdf = childcare_gdf[["name", "type", "tag", "quality", "geometry"]]

    # 4a. Process and integrate Maryland Food Bank data
    print("Processing Maryland Food Bank data...")
    mfb_gdf = gpd.read_file(INPUT_DIR / "maryland_food_bank.geojson")
    mfb_gdf["tag"] = mfb_gdf["type"]
    mfb_gdf["type"] = "food_pantry"
    mfb_gdf = mfb_gdf[["name", "type", "tag", "geometry"]]

    # 4b. Process and integrate Capital Area Food Bank data
    print("Processing Capital Area Food Bank data...")
    cafb_gdf = gpd.read_file(INPUT_DIR / "capital_area_food_bank.geojson")
    cafb_gdf["tag"] = cafb_gdf["type"]
    cafb_gdf["type"] = "food_pantry"
    cafb_gdf = cafb_gdf[["name", "type", "tag", "geometry"]]

    # 5. Combine all point datasets
    print("Combining all datasets...")
    all_points = pd.concat([
        points_gdf,
        financial_gdf,
        childcare_gdf,
        mfb_gdf,
        cafb_gdf
    ], ignore_index=True)

    # 6. Final processing and spatial join
    all_points["type_label"] = all_points["type"].str.replace("_", " ").str.title()
    all_points["tag_label"] = all_points["tag"].str.replace("_", " ").str.title()

    # Spatially join points with tracts to get GEOID20 and filter points within any tract
    md_tracts_union = grantees_gdf.unary_union
    points_in_md = all_points[all_points.within(md_tracts_union)]
    
    points_with_tracts = gpd.sjoin(points_in_md, grantees[["GEOID20", "geometry"]], how="left", predicate="within")
    points_with_tracts = points_with_tracts.drop(columns=['index_right'])

    # Determine if a point falls within a grantee tract
    grantee_geoids = set(grantees["GEOID20"])
    points_with_tracts["grantee"] = points_with_tracts["GEOID20"].isin(grantee_geoids)

    # 7. Write output files
    print("Writing output files...")
    # Write points located in grantee tracts to CSV
    grantee_points = points_with_tracts[points_with_tracts["grantee"]].copy()
    # Add lat/lng columns for CSV output
    grantee_points["lng"] = grantee_points.geometry.x
    grantee_points["lat"] = grantee_points.geometry.y
    grantee_points.drop(columns=["geometry"]).to_csv(OUTPUT_DIR / "grantee_points.csv", index=False)
    print(f"Saved {OUTPUT_DIR / 'grantee_points.csv'}")

    # Write a separate GeoJSON for each point type
    for unique_type in points_with_tracts["type"].unique():
        filename = OUTPUT_DIR / f"{unique_type}.geojson"
        points_subset = points_with_tracts[points_with_tracts["type"] == unique_type]
        points_subset.to_file(filename, driver="GeoJSON")
        print(f"Saved {filename}")

    # Write the processed grantees GeoDataFrame to GeoJSON
    grantees.to_file(OUTPUT_DIR / "grantees.geojson", driver="GeoJSON")
    print(f"Saved {OUTPUT_DIR / 'grantees.geojson'}")
    
    print("\nProcessing complete.")

if __name__ == "__main__":
    # To run with default caching behavior:
    run()
    
    # To force a redownload of the grantee data:
    # run(force_refresh_grantees=True)