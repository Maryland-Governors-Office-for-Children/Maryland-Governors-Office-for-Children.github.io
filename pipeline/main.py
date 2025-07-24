"""
Entrypoint for the ENOUGH Resource Map pipeline.
Orchestrates all major pipeline steps in order.
"""
from modules import (
    osm,
    financial,
    maryland_excel,
    maryland_food_bank,
    capital_area_food_bank,
    combine_data
)

REFRESH_OSM = False
REFRESH_FINANCIAL = False
REFRESH_CHILDCARE = False
REFRESH_FOODBANK = False

def main():
    print("Starting ENOUGH Resource Map pipeline...")
    # 1. Download OSM resource locations, if REFRESH_OSM
    if REFRESH_OSM:
        osm.run()

    # 2. Download FDIC and NCUA locations, if REFRESH_FINANCIAL
    if REFRESH_FINANCIAL:
        financial.run()

    # 3. Download MSDE Maryland Excels child care data, if REFRESH_CHILDCARE
    if REFRESH_CHILDCARE:
        maryland_excel.run()

    # 4. Download Maryland Food Bank and Capital Area Food Bank partner sites
    if REFRESH_FOODBANK:
        maryland_food_bank.run()
        capital_area_food_bank.run()

    # 4. Download Grantee locations and combine data
    combine_data.run()

    print("Pipeline complete.")


if __name__ == "__main__":
    main()