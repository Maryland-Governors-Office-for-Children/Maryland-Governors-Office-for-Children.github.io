# Methodology: ENOUGH Resource Map

## Overview

The ENOUGH Resource Map brings together multiple sources of public data to help Maryland residents find essential resources in their communities. This document explains where the data comes from, how it is processed, and how it is displayed on the map.

---

## Data Sources and Pipeline Steps

Here’s a step-by-step explanation of each data source and what it contributes:

### 1. OpenStreetMap (OSM) – Local Businesses and Services

- **What is it?**  
  OpenStreetMap is a global, crowd-sourced map project where volunteers add and update information about places and services.
- **What data is used?**  
  The pipeline queries OSM for locations such as grocery stores, laundromats, home and auto repair shops, pharmacies, barber/beauty shops, medical facilities, and more.
- **How is it processed?**  
  The script downloads all matching locations within Maryland’s boundaries, extracts their names, types, and specific tags (e.g., “supermarket” or “pharmacy”), and saves them for further processing.
- **Caveat:**  
  Because OSM is crowd-sourced, coverage and accuracy can vary. Areas with more active contributors will have more complete data, while some businesses may be missing in less-mapped regions.

### 2. FDIC and NCUA – Financial Institutions

- **What is it?**  
  - **FDIC:** The Federal Deposit Insurance Corporation provides data on all bank branches.
  - **NCUA:** The National Credit Union Administration provides data on credit union branches.
- **What data is used?**  
  - **FDIC:** All bank branches in Maryland, including their names and locations.
  - **NCUA:** All credit union branches in Maryland, including names, locations, and a set of additional services (such as bilingual services, financial counseling, and more).
- **How is it processed?**  
  The script downloads the latest data from both agencies, filters for Maryland locations, and saves them for integration.

### 3. Maryland Excels – Child Care Providers

- **What is it?**  
  Maryland Excels is the state’s quality rating and improvement system for child care and early education programs.
- **What data is used?**  
  All licensed child care providers in Maryland, including their names, types, locations, and their Maryland Excels quality rating (if available).
- **How is it processed?**  
  The script downloads provider data for each county, extracts relevant fields, and saves both a CSV and a GeoJSON file for mapping.
- **About the Quality Rating:**  
  The Maryland Excels rating is a scale from 1 to 5, but it is not a “bad-to-good” scale. All rated providers meet health and safety training requirements. The scale goes from “good” to “better,” reflecting additional quality standards.  
  [See what each rating means (PDF)](https://marylandexcels.org/wp-content/uploads/2024/06/Highlights-of-Quality-Rating.pdf)

### 4. Maryland Food Bank and Capital Area Food Bank – Food Assistance

- **What is it?**  
  - **Maryland Food Bank:** Provides locations of food pantries and partner agencies across Maryland.
  - **Capital Area Food Bank:** Provides locations of partner agencies in the greater Washington, DC region.
- **What data is used?**  
  Locations and names of all partner agencies, with additional program type information for Maryland Food Bank sites.
- **How is it processed?**  
  The script downloads the latest data from each organization’s public ArcGIS servers and save the locations for mapping.

### 5. Grantee Tracts – ENOUGH Act Grantee Areas

- **What is it?**  
  Geographic boundaries for communities served by ENOUGH Act grantees, including the grantee organization name and the type of grant track.
- **What data is used?**  
  The script downloads the latest grantee tract boundaries and combines them with all the resource data above.
- **How is it processed?**  
  - Each resource point is checked to see if it falls within a grantee tract.
  - The final output includes both all resources and a subset that are specifically within grantee communities.

---

## Data Integration and Processing

After collecting all the above data:

- All resource points are combined into a single dataset, with standardized fields for name, type, and tag (specific type).
- For each resource, the script determines if it is located within a grantee tract.
- The final data is exported as GeoJSON files (for mapping) and CSV files (for tabular analysis).
- Each resource type (grocery, childcare, financial, etc.) gets its own file for efficient loading and filtering on the map.

---

## Data Display on the Map

The interactive map displays all the above resources and allows users to filter by type, search for grantee organizations, and view details about each location.

### What Fields Are Shown?

- **All Resources:**  
  - **Name:** The name of the business or organization (if available).
  - **Type:** The general category (e.g., Grocery, Childcare, Financial, Food Pantry, etc.).
  - **Tag:** The specific type or program (e.g., “supermarket,” “pharmacy,” “Capital Area Food Bank Partner Agency”).
- **Financial Institutions (NCUA Credit Unions):**  
  - In addition to name, type, and tag, credit union locations may display special services, such as:
    - Bilingual services
    - Financial counseling
    - Credit builder programs
    - Free checking accounts
    - Payday alternative loans
    - And more (see map popups for details)
- **Child Care Providers:**  
  - The Maryland Excels quality rating is shown if available (1 to 5).
  - **Important:**  
    - The Maryland Excels rating is not a “bad-to-good” scale. All rated providers meet health and safety training requirements.  
    - The scale goes from “good” (1) to “better” (5), reflecting additional quality standards.  
    - [Learn more about Maryland Excels ratings (PDF)](https://marylandexcels.org/wp-content/uploads/2024/06/Highlights-of-Quality-Rating.pdf)

### Map Features

- **Filter by Resource Type:**  
  Users can toggle resource types on and off to focus on what they need.
- **Search for Grantee Organizations:**  
  A dropdown allows users to zoom to the area served by a specific ENOUGH Act grantee.
- **Legend:**  
  The map legend explains the color coding for different grantee tracks.

---

## Data Caveats and Limitations

- **OpenStreetMap (OSM) Data:**  
  OSM is crowd-sourced. Some areas may have incomplete or outdated information, especially where fewer volunteers contribute.
- **Timeliness:**  
  Data is updated regularly, but there may be a lag between real-world changes and updates in the source databases.
- **Accuracy:**  
  All data is provided as-is from public sources. Users should verify details with the listed organizations when possible.
