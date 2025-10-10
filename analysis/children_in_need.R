list.of.packages <- c(
  "data.table", "sf", "tidycensus", "tidyverse", "dotenv",
  "ggplot2", "scales"
)
new.packages <- list.of.packages[!(list.of.packages %in% installed.packages()[,"Package"])]
if(length(new.packages)) install.packages(new.packages)
suppressPackageStartupMessages(lapply(list.of.packages, require, character.only=T))

# Set your working directory
setwd("C:/git/ENOUGH-Resource-Map/")

api_key = Sys.getenv("CENSUS_API_KEY")
census_api_key(api_key)

grantees = st_read("docs/resource_map/assets/grantees.geojson")

acs_long = get_acs(
  geography = "tract",
  variables = c(
    under6_twoparents_inlaborforce = "B23008_004",
    under6_oneparentfather_inlaborforce = "B23008_010",
    under6_oneparentmother_inlaborforce = "B23008_013"
  ),
  year = 2023,
  state = "MD",
  geometry = TRUE
)

tract_geography = unique(acs_long[,c("GEOID")])
acs_agg = data.table(acs_long)[,.(under6_inneed = sum(estimate)), by=.(GEOID)]
need = merge(tract_geography, acs_agg, by="GEOID")

ggplot(need) + 
  geom_sf(aes(fill=under6_inneed), color=NA) +
  theme_void() +
  labs(fill="Children under 6 in\nhouseholds where all parent(s)\nare in the labor force")

demand_grantees = merge(data.table(demand), data.table(grantees), by.x="GEOID", by.y="GEOID20")
demand_grantees_agg = demand_grantees[,.(under6_inneed=sum(under6_inneed)), by=.(
  ORGANIZATION_NAME, GOC_TRACK_TYPE
)]
fwrite(demand_grantees_agg, "analysis/grantee_children_in_need_of_childcare.csv")