# https://experience.arcgis.com/experience/fe4fdacfd20b46c08dac240ca8dd6192

import os
import json
import re
import requests

# Mapping for acronyms found in layer titles to their full names.
ACRONYM_MAP = {
    "CSFP": "Commodity Supplemental Food Program",
    "DSS": "Department of Social Services",
    "EFO": "Emergency Feeding Organization",
    "MFB": "Maryland Food Bank",
    "POTG": "Pantry on the Go",
    "RDO": "Regional Distributing Organization",
    "TEFAP": "The Emergency Food Assistance Program",
}

# Definitive configuration with precise WHERE clauses based on user-provided data.
LAYERS_TO_DOWNLOAD = [
    # --- Separate Feature Services ---
    {
        "title": "EFO Downstream Partners",
        "url": "https://services6.arcgis.com/z5rKj2pMbYQAvHJ4/arcgis/rest/services/EFODownstreamPartnerListFY24Q4_Geocoded1/FeatureServer/0",
        "name_field": "USER_AGENCY_NAME__ERA_",
        "where_clause": "1=1"
    },
    {
        "title": "RDO Downstream Partners",
        "url": "https://services6.arcgis.com/z5rKj2pMbYQAvHJ4/arcgis/rest/services/RDODownstreamPartnerListFY24Q4_Geocoded/FeatureServer/0",
        "name_field": "USER_AGENCY_NAME",
        "where_clause": "1=1"
    },
    # --- Layers from the main PartnerAgencies Feature Service ---
    # {
    #     "title": "Inactive Agencies",
    #     "url": "https://services6.arcgis.com/z5rKj2pMbYQAvHJ4/arcgis/rest/services/PartnerAgencies070123to063024/FeatureServer/0",
    #     "name_field": "Name",
    #     "where_clause": "Status IN ('INACTIVE', 'INACTIVEAG', 'SUSPENDED', 'PAST DUE')"
    # },
    {
        "title": "CSFP and Senior",
        "url": "https://services6.arcgis.com/z5rKj2pMbYQAvHJ4/arcgis/rest/services/PartnerAgencies070123to063024/FeatureServer/0",
        "name_field": "Name",
        "where_clause": "Agency_Category = 'SENIOR'"
    },
    {
        "title": "DSS",
        "url": "https://services6.arcgis.com/z5rKj2pMbYQAvHJ4/arcgis/rest/services/PartnerAgencies070123to063024/FeatureServer/0",
        "name_field": "Name",
        "where_clause": "Program_Type = 'DSS'"
    },
    {
        "title": "POTG",
        "url": "https://services6.arcgis.com/z5rKj2pMbYQAvHJ4/arcgis/rest/services/PartnerAgencies070123to063024/FeatureServer/0",
        "name_field": "Name",
        "where_clause": "Program_Type = 'POTG'"
    },
    {
        "title": "TEFAP: EFO",
        "url": "https://services6.arcgis.com/z5rKj2pMbYQAvHJ4/arcgis/rest/services/PartnerAgencies070123to063024/FeatureServer/0",
        "name_field": "Name",
        "where_clause": "Program_Type = 'TEFAP: EFO'"
    },
    {
        "title": "TEFAP",
        "url": "https://services6.arcgis.com/z5rKj2pMbYQAvHJ4/arcgis/rest/services/PartnerAgencies070123to063024/FeatureServer/0",
        "name_field": "Name",
        "where_clause": "Program_Type = 'TEFAP'"
    },
    {
        "title": "MFB Kids Programs", # Grouped title as data is not more specific
        "url": "https://services6.arcgis.com/z5rKj2pMbYQAvHJ4/arcgis/rest/services/PartnerAgencies070123to063024/FeatureServer/0",
        "name_field": "Name",
        "where_clause": "Program_Type = 'MFB KIDS'"
    },
    {
        "title": "Network Partners: Higher Ed",
        "url": "https://services6.arcgis.com/z5rKj2pMbYQAvHJ4/arcgis/rest/services/PartnerAgencies070123to063024/FeatureServer/0",
        "name_field": "Name",
        "where_clause": "Program_Type = 'NETPARTNER' AND Agency_Category = 'HIGHER ED'"
    },
    {
        "title": "Network Partners: Backpacks",
        "url": "https://services6.arcgis.com/z5rKj2pMbYQAvHJ4/arcgis/rest/services/PartnerAgencies070123to063024/FeatureServer/0",
        "name_field": "Name",
        "where_clause": "Program_Type = 'NETPARTNER' AND Agency_Category = 'BKPCK NP'"
    },
    {
        "title": "Network Partners: Pantry Programs",
        "url": "https://services6.arcgis.com/z5rKj2pMbYQAvHJ4/arcgis/rest/services/PartnerAgencies070123to063024/FeatureServer/0",
        "name_field": "Name",
        "where_clause": "Program_Type = 'NETPARTNER' AND Agency_Category = 'PANTRY'"
    },
    {
        "title": "Network Partners: Meal Programs",
        "url": "https://services6.arcgis.com/z5rKj2pMbYQAvHJ4/arcgis/rest/services/PartnerAgencies070123to063024/FeatureServer/0",
        "name_field": "Name",
        "where_clause": "Program_Type = 'NETPARTNER' AND Agency_Category IN ('SOUP KITCH', 'EMGSHLTR')"
    },
    {
        "title": "Network Partners: RDOs",
        "url": "https://services6.arcgis.com/z5rKj2pMbYQAvHJ4/arcgis/rest/services/PartnerAgencies070123to063024/FeatureServer/0",
        "name_field": "Name",
        "where_clause": "Program_Type = 'NETPARTNER' AND Agency_Category IN ('SUB RDO', 'SDO')"
    }
]


OUTPUT_FILE = "input/maryland_food_bank.geojson"

def expand_title(title: str) -> str:
    """Expands known acronyms in a layer title to their full names."""
    expanded = title
    for acronym, full_name in sorted(ACRONYM_MAP.items(), key=lambda item: len(item[0]), reverse=True):
        expanded = re.sub(r'\b' + re.escape(acronym) + r'\b', full_name, expanded)
    return expanded

def fetch_and_process_layer(layer_info: dict) -> list:
    """
    Fetches data from an ArcGIS layer URL using a specific WHERE clause and
    returns a list of formatted GeoJSON features.
    """
    url = layer_info.get("url")
    name_field = layer_info.get("name_field")
    original_title = layer_info.get("title")
    where_clause = layer_info.get("where_clause")
    expanded_type = expand_title(original_title)
    
    params = {
        "where": where_clause,
        "outFields": name_field,
        "f": "geojson",
        "outSR": "4326"
    }
    
    try:
        print(f"Downloading data for: {original_title}")
        response = requests.get(f"{url}/query", params=params)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"  Error fetching {url}: {e}")
        return []
    except json.JSONDecodeError:
        print(f"  Error decoding JSON from {url}")
        return []

    processed_features = []
    for feature in data.get("features", []):
        properties = feature.get("properties", {})
        name = properties.get(name_field)
        
        processed_features.append({
            "type": "Feature",
            "geometry": feature.get("geometry"),
            "properties": {
                "type": expanded_type,
                "name": name.strip() if isinstance(name, str) else name
            }
        })
        
    print(f"  Processed {len(processed_features)} features.")
    return processed_features

def run():
    """
    Downloads all Maryland Food Bank layers using specific filters and saves
    the combined result as a single GeoJSON file.
    """
    print("Starting Maryland Food Bank data download...")
    all_features = []
    
    for layer in LAYERS_TO_DOWNLOAD:
        features = fetch_and_process_layer(layer)
        all_features.extend(features)
        
    # Create the output directory if it doesn't exist.
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    output_geojson = {
        "type": "FeatureCollection",
        "features": all_features
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output_geojson, f, indent=2)

    print(f"\nSuccess! Combined {len(all_features)} features.")
    print(f"Data saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    run()