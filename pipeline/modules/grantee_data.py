import os
import re
import geopandas as gpd
from pathlib import Path
from shapely.geometry import Point, Polygon, LineString
import requests


def fetch_arcgis_data(url, params, page_size=1000):
    '''
    Fetches data from an ArcGIS REST service endpoint with pagination and returns it as a GeoDataFrame.
    '''
    print(f'Fetching data from: {url}')
    all_features = []
    result_offset = 0
    total_fetched = 0
    wkid = None
    geom_type = None
    while True:
        paged_params = params.copy()
        paged_params['resultOffset'] = result_offset
        paged_params['resultRecordCount'] = page_size
        try:
            response = requests.get(url, params=paged_params, timeout=60)
            response.raise_for_status()
            data = response.json()
            if 'features' not in data or not data['features']:
                break
            if wkid is None:
                try:
                    wkid = data['spatialReference']['latestWkid']
                except KeyError:
                    print('Warning: Could not determine WKID from response. CRS will not be set.')
                    wkid = None
            if geom_type is None:
                geom_type = data.get('geometryType')
            all_features.extend(data['features'])
            fetched = len(data['features'])
            total_fetched += fetched
            print(f"Fetched {fetched} features (total so far: {total_fetched})...")
            if fetched < page_size:
                break
            result_offset += page_size
        except requests.exceptions.RequestException as e:
            print(f'HTTP Request failed: {e}')
            break
        except (KeyError, json.JSONDecodeError) as e:
            print(f'Failed to parse JSON response: {e}')
            break
    if not all_features:
        print('No features found in the response.')
        return None
    attributes_list = []
    geometry_list = []
    for feature in all_features:
        attributes_list.append(feature['attributes'])
        geom = feature.get('geometry')
        if not geom:
            geometry_list.append(None)
            continue
        if geom_type == 'esriGeometryPoint':
            geometry_list.append(Point(geom['x'], geom['y']))
        elif geom_type == 'esriGeometryPolygon':
            geometry_list.append(Polygon(geom['rings'][0]))
        elif geom_type == 'esriGeometryPolyline':
            geometry_list.append(LineString(geom['paths'][0]))
        else:
            geometry_list.append(None)
    gdf = gpd.GeoDataFrame(attributes_list, geometry=geometry_list)
    if wkid:
        print(f'Setting CRS to EPSG:{wkid}')
        gdf.set_crs(f'EPSG:{wkid}', inplace=True)
    return gdf


def run():
    """
    Fetches grantee data from ArcGIS REST endpoint, cleans GOC_TRACK_TYPE, and saves as GeoJSON.
    """
    url = "https://services.arcgis.com/njFNhDsUCentVYJW/arcgis/rest/services/Grantees_20250623/FeatureServer/0/query"
    params = {
        'f': 'json',
        'where': '1=1',
        'returnGeometry': 'true',
        'outFields': '*'
    }
    print("Fetching grantee data from ArcGIS REST endpoint...")
    gdf = fetch_arcgis_data(url, params)
    if gdf is None:
        print("No data fetched.")
        return
    # Clean GOC_TRACK_TYPE
    if "GOC_TRACK_TYPE" in gdf.columns:
        gdf["GOC_TRACK_TYPE"] = gdf["GOC_TRACK_TYPE"].apply(
            lambda s: re.sub(r"^Track [0-9]+: ", "", s) if isinstance(s, str) else s
        )
    # Transform CRS to 4326 before saving
    gdf = gdf.to_crs(epsg=4326)
    # Ensure output directory exists
    out_path = Path("input") / "grantees_data.geojson"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(out_path, driver="GeoJSON")
    print(f"Saved cleaned grantee data to {out_path}")
