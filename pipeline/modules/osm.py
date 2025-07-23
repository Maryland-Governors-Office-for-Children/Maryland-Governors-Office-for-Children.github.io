import geopandas as gpd
import requests
import csv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm
from time import sleep

RESOURCE_TYPES = {
    'grocery': [
        'amenity=marketplace',
        'shop=bakery',
        'shop=butcher',
        'shop=cheese',
        'shop=convenience',
        'shop=dairy',
        'shop=deli',
        'shop=delicatessen',
        'shop=eggs',
        'shop=farm',
        'shop=fish',
        'shop=fishmonger',
        'shop=food',
        'shop=frozen_food',
        'shop=general',
        'shop=greengrocer',
        'shop=grocery',
        'shop=health_food',
        'shop=pastry',
        'shop=pasta',
        'shop=seafood',
        'shop=supermarket',
        'shop=wholesale'
    ],
    'laundry': [
        'shop=dry_cleaning',
        'shop=laundry',
    ],
    'home_repair': [
        'shop=building_materials',
        'shop=doityourself',
        'shop=hardware',
        'shop=paint',
        'shop=power_tools',
        'shop=tools'
    ],
    'auto_repair': [
        'shop=auto_parts',
        'shop=car_parts',
        'shop=car_repair',
        'shop=truck_parts',
        'shop=truck_repair',
        'shop=tyres'
    ],
    'pharmacy': [
        'amenity=pharmacy',
        'healthcare=pharmacy',
        'shop=pharmacy'
    ],
    'barber_beauty': [
        'shop=beauty',
        'shop=hairdresser',
        'shop=hairdresser_supply'
    ],
    'medical': [
        'shop=health',
        'shop=medical_supply',
        'shop=medical',
        'amenity=hospital',
        'amenity=clinic',
        'amenity=doctors',
        'amenity=dentist',
        'healthcare=alternative',
        'healthcare=audiologist',
        'healthcare=birthing_centre',
        'healthcare=blood_bank',
        'healthcare=blood_donation',
        'healthcare=centre',
        'healthcare=clinic',
        'healthcare=community_health_worker',
        'healthcare=counselling',
        'healthcare=dentist',
        'healthcare=dialysis',
        'healthcare=doctor',
        'healthcare=hospice',
        'healthcare=hospital',
        'healthcare=laboratory',
        'healthcare=midwife',
        'healthcare=nurse',
        'healthcare=occupational_therapist',
        'healthcare=optometrist',
        'healthcare=physiotherapist',
        'healthcare=podiatrist',
        'healthcare=psychotherapist',
        'healthcare=rehabilitation',
        'healthcare=sample_collection',
        'healthcare=speech_therapist',
        'healthcare=vaccination_centre',
        'healthcare=postpartum_care',
        'healthcare=yes'
    ]
}


def query_overpass_resources(resource_queries, bbox, retries=3, backoff_factor=0.5, backoff_jitter=0.1, status_forcelist=(429, 500, 502, 503, 504)):
    """Query Overpass API for a list of resource queries within bbox."""
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        backoff_jitter=backoff_jitter,
        status_forcelist=status_forcelist
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    # Build Overpass QL for all queries
    query_parts = []
    for q in resource_queries:
        key, value = q.split("=")
        if value == "*":
            query_parts.append(f'node["{key}"]({bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]});')
            query_parts.append(f'way["{key}"]({bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]});')
            query_parts.append(f'relation["{key}"]({bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]});')
        else:
            query_parts.append(f'node["{key}"="{value}"]({bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]});')
            query_parts.append(f'way["{key}"="{value}"]({bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]});')
            query_parts.append(f'relation["{key}"="{value}"]({bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]});')
    query = f"""
    [out:json][timeout:180];
    (
        {"".join(query_parts)}
    );
    out center;
    """
    url = "http://overpass-api.de/api/interpreter"
    headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
    try:
        response = session.post(url, data={'data': query}, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Overpass API query failed: {e}")
        return None

def run():
    # Load the shapefile of Maryland for total bounding box
    shapefile_path = 'input/imap_tracts/Maryland_Census_Boundaries_-_Census_Tracts_2020.shp'
    gdf = gpd.read_file(shapefile_path)
    gdf = gdf.to_crs(4326)

    minx, miny, maxx, maxy = gdf.total_bounds
    global_bbox = (minx, miny, maxx, maxy)
    # Fetch resources for each type
    resources_by_type = {}
    for resource_type, queries in tqdm(RESOURCE_TYPES.items(), desc="Fetching resources by type"):
        print(f"Querying Overpass for {resource_type}...")
        result = query_overpass_resources(queries, global_bbox)
        if result:
            resources_by_type[resource_type] = result['elements']
        else:
            resources_by_type[resource_type] = []
        sleep(10)


    # Write resources_by_type to CSV with columns: name, type, lat, lng
    cbc_csv_path = 'input/resources.csv'
    cbc_rows = []
    for resource_type, elements in resources_by_type.items():
        for el in elements:
            # Get coordinates
            if 'lat' in el and 'lon' in el:
                lat, lng = el['lat'], el['lon']
            elif 'center' in el and 'lat' in el['center'] and 'lon' in el['center']:
                lat, lng = el['center']['lat'], el['center']['lon']
            else:
                continue
            # Get name if available
            tags = el.get('tags', {})
            name_priority = ['name', 'operator']
            name = ''
            for tag_name in name_priority:
                name = tags.get(tag_name, '')
                if name != '':
                    break

            # Get original tag
            tag_priority = ['shop', 'amenity', 'healthcare']
            tag = ''
            for tag_name in tag_priority:
                tag = tags.get(tag_name, '')
                if tag != '':
                    break
            if name == '' and tag != '':
                name = f'Unnamed {tag}'
            cbc_rows.append({'name': name, 'type': resource_type, 'tag': tag, 'lat': lat, 'lng': lng})

    cbc_columns = ['name', 'type', 'tag', 'lat', 'lng']
    try:
        with open(cbc_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=cbc_columns)
            writer.writeheader()
            for row in cbc_rows:
                writer.writerow(row)
        print(f"Successfully wrote data to {cbc_csv_path}")
    except IOError as e:
        print(f"I/O error writing to CSV file: {e}")


if __name__ == '__main__':
    run()