import requests
import pandas as pd
import urllib.parse
import json
import os

# This data is used to map IDs and codes from the API to human-readable names.
REFERENCE_DATA = {
  "achievements": [
    {"name": "Accredited Program", "id": 49, "type": "ACHIEVEMENT"},
    {"name": "American Montessori Society (AMS)", "id": 42, "type": "ACCREDITATION"},
    {"name": "Association Montessori International / USA (AMI/USA)", "id": 48, "type": "ACCREDITATION"},
    {"name": "Association of Independent Maryland Schools (AIMS)", "id": 41, "type": "ACCREDITATION"},
    {"name": "Association of Waldorf Schools of North America (AWSNA)", "id": 43, "type": "ACCREDITATION"},
    {"name": "Asthma & Allergy Friendly", "id": 163, "type": "ACHIEVEMENT"},
    {"name": "Asthma-Friendly Program", "id": 50, "type": "ACHIEVEMENT"},
    {"name": "Cognia Early Learning Accreditation", "id": 40, "type": "ACCREDITATION"},
    {"name": "Council on Accreditation / After-School Accreditation (COA/ASA)", "id": 39, "type": "ACCREDITATION"},
    {"name": "Cultural and Linguistic Competency", "id": 51, "type": "ACHIEVEMENT"},
    {"name": "Eco-Friendly Program", "id": 54, "type": "ACHIEVEMENT"},
    {"name": "Family Engagement", "id": 233, "type": "ACHIEVEMENT"},
    {"name": "Health and Wellness", "id": 52, "type": "ACHIEVEMENT"},
    {"name": "Judy Center", "id": 235, "type": "ACHIEVEMENT"},
    {"name": "Maryland Accreditation", "id": 38, "type": "ACCREDITATION"},
    {"name": "Middle States Association of Colleges and Schools Commission on Elementary and Secondary Schools (MSA-CESS)", "id": 44, "type": "ACCREDITATION"},
    {"name": "Military Child Care in Your Neighborhood", "id": 234, "type": "ACHIEVEMENT"},
    {"name": "National Accreditation Commission (NAC)", "id": 45, "type": "ACCREDITATION"},
    {"name": "National Association for Family Child Care (NAFCC)", "id": 37, "type": "ACCREDITATION"},
    {"name": "National Association for the Education of Young Children (NAEYC)", "id": 46, "type": "ACCREDITATION"},
    {"name": "National Early Childhood Program Accreditation (NECPA)", "id": 47, "type": "ACCREDITATION"},
    {"name": "Quality Business Practices", "id": 53, "type": "ACHIEVEMENT"}
  ]
}

def build_lookup_maps(reference_data):
    achievements_map = {item['id']: item for item in reference_data['achievements']}
    return achievements_map

def process_provider_record_for_csv(record, achievements_map):
    accreditations, achievements = [], []
    if 'achievements' in record and isinstance(record['achievements'], list):
        for ach_item in record['achievements']:
            ach_id = ach_item.get('id')
            if ach_id in achievements_map:
                ach_info = achievements_map[ach_id]
                if ach_info['type'] == 'ACCREDITATION':
                    accreditations.append(ach_info['name'])
                else:
                    achievements.append(ach_info['name'])
    area_ratings = record.get('area_ratings', {})
    if not isinstance(area_ratings, dict):
        area_ratings = {}
    return {
        'name': record.get('name'), 'dba': record.get('dba'),
        'type': record.get('type'), 'license': record.get('license'),
        'phone': record.get('phone'), 'website': record.get('website'),
        'overall_rating': record.get('rating'), 'expiration_date': record.get('exp_date'),
        'street_address': record.get('street_address'), 'city': record.get('city'),
        'zip_code': record.get('zip'), 'county': record.get('county'),
        'latitude': record.get('lat'), 'longitude': record.get('long'),
        'provider_id': record.get('p_id'),
        'accreditations': ", ".join(sorted(accreditations)),
        'achievements': ", ".join(sorted(achievements)),
        'rating_licensing_compliance': area_ratings.get('LIC'),
        'rating_staff_qualifications': area_ratings.get('STF'),
        'rating_accreditation_rating_scales': area_ratings.get('ACR'),
        'rating_developmentally_appropriate_learning': area_ratings.get('DAP'),
        'rating_administrative_policies': area_ratings.get('ADM'),
    }

def create_geojson_feature(record):
    try:
        longitude = float(record.get('long'))
        latitude = float(record.get('lat'))
        overall_rating = record.get('rating')
        try:
            quality = int(overall_rating) if overall_rating is not None else None
        except (ValueError, TypeError):
            quality = None
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [longitude, latitude]
            },
            "properties": {
                "name": record.get('name'),
                "tag_label": record.get('type'),
                "quality": quality
            }
        }
        return feature
    except (TypeError, ValueError):
        return None

def run(
    csv_output_filename="input/maryland_childcare_data.csv",
    geojson_output_filename="input/childcare.geojson",
    counties_to_scrape=None
):
    """
    Download Maryland childcare locations and quality ratings, save as CSV and GeoJSON.
    Idempotent: skips download if outputs exist.
    """
    if counties_to_scrape is None:
        counties_to_scrape = [
            "Allegany", "Anne Arundel", "Baltimore City", "Baltimore", "Calvert", "Caroline", "Carroll", "Cecil", "Charles", "Dorchester", "Frederick", "Garrett", "Harford", "Howard", "Kent", "Montgomery", "Prince George's", "Queen Anne's", "Saint Mary's", "Somerset", "Talbot", "Washington", "Wicomico", "Worcester"
        ]
    if os.path.exists(csv_output_filename) and os.path.exists(geojson_output_filename):
        print("Childcare data already exists. Skipping download.")
        return

    base_url = "https://excels.marylandexcels.org/directory/search"
    achievements_map = build_lookup_maps(REFERENCE_DATA)
    all_providers_for_csv = []
    all_features_for_geojson = []

    for county in counties_to_scrape:
        encoded_county = urllib.parse.quote(county)
        url = f"{base_url}?county={encoded_county}&countyMode=true"
        print(f"Fetching data for {county} from: {url}")
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            provider_data = response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data for {county}: {e}")
            continue
        except json.JSONDecodeError:
            print(f"Error decoding JSON for {county}. The response may not be valid JSON.")
            continue
        if provider_data:
            print(f"Successfully fetched {len(provider_data)} records for {county}.")
            for record in provider_data:
                processed_csv_record = process_provider_record_for_csv(record, achievements_map)
                all_providers_for_csv.append(processed_csv_record)
                geojson_feature = create_geojson_feature(record)
                if geojson_feature:
                    all_features_for_geojson.append(geojson_feature)
        else:
            print(f"Could not fetch data for {county}. Skipping.")
        print("-" * 30)

    # --- Save CSV File ---
    if all_providers_for_csv:
        print("Saving data to CSV file...")
        df = pd.DataFrame(all_providers_for_csv)
        try:
            df.to_csv(csv_output_filename, index=False, encoding='utf-8')
            print(f"Successfully saved {len(df)} records to '{csv_output_filename}'")
        except Exception as e:
            print(f"Error saving data to CSV: {e}")
    else:
        print("No data collected for CSV output.")

    # --- Save GeoJSON File ---
    if all_features_for_geojson:
        print("\nSaving data to GeoJSON file...")
        geojson_feature_collection = {
            "type": "FeatureCollection",
            "crs": {
                "type": "name",
                "properties": {
                    "name": "urn:ogc:def:crs:OGC:1.3:CRS84"
                }
            },
            "features": all_features_for_geojson
        }
        try:
            with open(geojson_output_filename, 'w', encoding='utf-8') as f:
                json.dump(geojson_feature_collection, f, indent=2)
            print(f"Successfully saved {len(all_features_for_geojson)} features to '{geojson_output_filename}'")
        except Exception as e:
            print(f"Error saving data to GeoJSON: {e}")
    else:
        print("No valid geographic data collected for GeoJSON output.")
