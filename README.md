# Glacier Surface Area Change Detection: Quelccaya Ice Cap (Peru)

## Overview

This project quantifies long-term glacier surface area change at the Quelccaya Ice Cap (Peru) using Landsat satellite imagery and Google Earth Engine.

A parameterized Python workflow was developed to:
- Extract glacier/snow-covered extent using spectral indices
- Apply terrain-based filtering (elevation + slope)
- Compute glacier surface area over time
- Generate visual outputs (time series and animation)

The analysis spans **1990–2024**, providing a consistent estimate of glacier retreat in one of the world’s largest tropical ice caps.

---

## Key Results

- Glacier area declined from ~58 km² (1990) to ~37 km² (2024)  
- Total estimated loss: **~36–37%**  
- Strong long-term declining trend consistent with literature  
- Short-term variability reflects seasonal snow and classification sensitivity  

---

## Study Area

- **Location:** Quelccaya Ice Cap, Peru  
- **Region of Interest (ROI):**
[-70.9, -14.00]
[-70.7, -14.00]
[-70.7, -13.83]
[-70.9, -13.83]

- Elevation range: ~5000–5700 m  
- One of the largest tropical ice masses globally  

---

## Data

- **Landsat Collection 2 Level-2 Surface Reflectance**
  - Landsat 5 (pre-1999)
  - Landsat 7 (1999–2012)
  - Landsat 8 (2013–present)

- Temporal coverage: **1990–2024**
- Temporal resolution: **every 2 years**
- Seasonal filter: **August–October (dry season)**

---

## Methodology

### 1. Image Selection
- Filter by ROI and time window (Aug–Oct)
- Cloud cover threshold: < 20%
- Generate median composite per year

---

### 2. Preprocessing
- Apply Landsat Level-2 scaling:
Reflectance = DN × 0.0000275 − 0.2


---

### 3. Glacier Detection (NDSI)

The Normalized Difference Snow Index (NDSI) is computed as:
NDSI = (Green − SWIR) / (Green + SWIR)

Band selection depends on sensor:

| Sensor        | Green Band | SWIR Band |
|--------------|-----------|----------|
| Landsat 5/7  | SR_B2     | SR_B5    |
| Landsat 8    | SR_B3     | SR_B6    |

---

### 4. Classification Refinement

To improve classification accuracy:

- **NDSI threshold:** > 0.45  
- **Elevation filter:** > 5100 m  
- **Slope filter:** < 50°  
- **Connected pixel filter:** remove clusters < 40 pixels  

These filters reduce:
- Seasonal snow contamination  
- Steep terrain misclassification  
- Isolated noise  

---

### 5. Area Calculation

- Convert binary glacier mask to area using pixel area  
- Aggregate using Earth Engine `reduceRegion`  
- Convert results to km²  

---

### 6. Time Series Analysis

- Compute glacier area for each year  
- Calculate percentage change between consecutive observations  

---

### 7. Visualization

#### 📊 Time Series Plot
- Glacier area vs. year  
- Annotated total loss (absolute and percentage)

#### 🎞️ Animation (GIF)
- Shows spatial evolution of glacier extent  
- Cyan overlay represents detected glacier/snow-covered area  

---

## Outputs

- `quelccaya_glacier_area_results.csv`  
  → Glacier area and % change  

- `quelccaya_glacier_area_change_clean.png`  
  → Time series visualization  

- `quelccaya_glacier_change.gif`  
  → Animated glacier evolution  

---

## Parameters

```python
START_MONTH_DAY = "08-01"
END_MONTH_DAY = "10-30"
CLOUD_COVER_THRESHOLD = 20

NDSI_THRESHOLD = 0.45
ELEVATION_THRESHOLD = 5100
SLOPE_THRESHOLD = 50
MIN_CONNECTED_PIXELS = 40

```

---

## Status
Completed
