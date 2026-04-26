# Glacier Surface Area Change Detection: Quelccaya Ice Cap (Peru)

## Overview

This project quantifies changes in glacier surface area over time using satellite imagery and geospatial analysis. The focus is the Quelccaya Ice Cap in Peru, one of the largest tropical glaciers in the world.

The analysis uses Landsat imagery to extract glacier extent across multiple years and evaluates long-term surface area loss.

## Objectives

* Detect glacier extent using satellite imagery
* Quantify surface area changes over time
* Estimate the rate of glacier retreat
* Visualize spatial and temporal glacier dynamics

## Study Area

* Location: Quelccaya Ice Cap, Peru
* Coordinates: Approx. (-13.93, -70.83)

## Data

* Landsat imagery (1985–2024)

## Methodology

1. Select cloud-free satellite images for selected years
2. Compute NDSI (Normalized Difference Snow Index)
3. Apply threshold to extract glacier extent
4. Convert raster masks to area (km²)
5. Analyze changes over time

## Expected Outputs

* Glacier extent maps for each year
* Time series of glacier area
* Area change statistics
* Visual comparison of glacier retreat

## Tools

* Google Earth Engine / Python
* Raster processing (rasterio)
* Geospatial analysis (GeoPandas)
* Visualization (Matplotlib / Folium)

## Project Structure

* `data/` → processed and exported data
* `scripts/` → analysis scripts
* `outputs/` → maps and figures

## Status

Project initialization phase.

