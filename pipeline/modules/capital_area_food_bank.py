import os
import json
import requests

# Configuration for the Capital Area Food Bank endpoint
URL = "https://services.arcgis.com/oCjyzxNy34f0pJCV/arcgis/rest/services/Active_Agencies_Last_45_Days/FeatureServer/0"
NAME_FIELD = "name"
OUTPUT_FILE = "input/capital_area_food_bank.geojson"

def run():
    """
    Downloads all active agency data from the Capital Area Food Bank endpoint
    and saves it as a GeoJSON file.
    """
    print("Starting Capital Area Food Bank data download...")

    # Parameters for the ArcGIS REST API query
    params = {
        "where": "1=1",          # Get all features
        "outFields": NAME_FIELD, # Only request the name field
        "f": "geojson",          # Request output in GeoJSON format
        "outSR": "4326"          # Request standard WGS 84 coordinates
    }

    try:
        response = requests.get(f"{URL}/query", params=params)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from the server: {e}")
        return
    except json.JSONDecodeError:
        print("Error decoding JSON from the server response.")
        return

    all_features = []
    for feature in data.get("features", []):
        properties = feature.get("properties", {})
        site_name = properties.get(NAME_FIELD)

        # Skip any features that might be missing a name
        if not site_name:
            continue

        # Create a simplified feature with only the required fields
        processed_feature = {
            "type": "Feature",
            "geometry": feature.get("geometry"),
            "properties": {
                "type": "Capital Area Food Bank Partner Agency",
                "name": site_name.strip()
            }
        }
        all_features.append(processed_feature)

    # Create the output directory if it doesn't exist
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    # Create the final GeoJSON FeatureCollection
    output_geojson = {
        "type": "FeatureCollection",
        "features": all_features
    }

    # Save the combined data to the output file
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output_geojson, f, indent=2)

    print(f"\nSuccess! Processed {len(all_features)} features.")
    print(f"Data saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    run()