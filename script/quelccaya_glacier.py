import os
import requests
import imageio.v2 as imageio

import ee
import pandas as pd
import matplotlib.pyplot as plt


# =====================================================
# 1. INITIALISE EARTH ENGINE
# =====================================================

ee.Initialize()


# =====================================================
# 2. STUDY AREA AND PARAMETERS
# =====================================================

# Study area: Quelccaya Ice Cap, Peru
roi = ee.Geometry.Polygon([
    [
        [-70.9, -14.00],
        [-70.7, -14.00],
        [-70.7, -13.83],
        [-70.9, -13.83]
    ]
])

# Analysis parameters
START_MONTH_DAY = "08-01"
END_MONTH_DAY = "10-30"
CLOUD_COVER_THRESHOLD = 20

NDSI_THRESHOLD = 0.45 # lower more permissive
ELEVATION_THRESHOLD = 5100 # lower more permissive
SLOPE_THRESHOLD = 50 # higher more permissive
MIN_CONNECTED_PIXELS = 40 # lower more permissive

YEARS = list(range(1990, 2025, 2))

OUTPUT_FOLDER = r"C:\Python_Projects\Environmental_DS_Portfolio"
FRAMES_FOLDER = os.path.join(OUTPUT_FOLDER, "frames")


# =====================================================
# 3. LANDSAT PREPROCESSING
# =====================================================

def scale_landsat_l2(image):
    optical = image.select("SR_B.*").multiply(0.0000275).add(-0.2)
    return image.addBands(optical, None, True)


def get_landsat_collection(year):
    start = f"{year}-{START_MONTH_DAY}"
    end = f"{year}-{END_MONTH_DAY}"

    if year < 1999:
        dataset = "LANDSAT/LT05/C02/T1_L2"
    elif year < 2013:
        dataset = "LANDSAT/LE07/C02/T1_L2"
    else:
        dataset = "LANDSAT/LC08/C02/T1_L2"

    return (
        ee.ImageCollection(dataset)
        .filterBounds(roi)
        .filterDate(start, end)
        .filterMetadata("CLOUD_COVER", "less_than", CLOUD_COVER_THRESHOLD)
        .map(scale_landsat_l2)
    )


def get_landsat_bands(year):
    if year < 2013:
        return "SR_B2", "SR_B5"  # Green, SWIR1 for Landsat 5/7
    return "SR_B3", "SR_B6"      # Green, SWIR1 for Landsat 8


# =====================================================
# 4. GLACIER MASK
# =====================================================

def create_glacier_mask(year):
    image = get_landsat_collection(year).median().clip(roi)

    green_band, swir_band = get_landsat_bands(year)

    # NDSI = (Green - SWIR) / (Green + SWIR)
    ndsi = image.normalizedDifference([green_band, swir_band]).rename("NDSI")

    # Elevation filter to reduce seasonal snow contamination
    dem = ee.Image("USGS/SRTMGL1_003").clip(roi)
    high_alt = dem.gt(ELEVATION_THRESHOLD)

    # Slope filter to reduce steep-terrain misclassification
    slope = ee.Terrain.slope(dem)
    low_slope = slope.lt(SLOPE_THRESHOLD)

    # Glacier/snow-covered area mask
    glacier = (
        ndsi.gt(NDSI_THRESHOLD)
        .And(high_alt)
        .And(low_slope)
        .rename("glacier")
    )

    # Remove small isolated patches
    connected = glacier.connectedPixelCount(100, True)
    glacier = glacier.updateMask(connected.gt(MIN_CONNECTED_PIXELS))

    return glacier


# =====================================================
# 5. AREA CALCULATION
# =====================================================

def calculate_area(year):
    glacier = create_glacier_mask(year)

    area_image = glacier.multiply(ee.Image.pixelArea())

    area = area_image.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=roi,
        scale=30,
        maxPixels=1e13
    )

    area_km2 = ee.Number(area.get("glacier")).divide(1e6).getInfo()

    return {
        "year": year,
        "area_km2": area_km2
    }


results = [calculate_area(year) for year in YEARS]

df = pd.DataFrame(results)

df["percent_change_from_previous_observation"] = (
    df["area_km2"].pct_change() * 100
)

df["area_km2"] = df["area_km2"].round(2)
df["percent_change_from_previous_observation"] = (
    df["percent_change_from_previous_observation"].round(2)
)

print(df)


# =====================================================
# 6. EXPORT TABLE
# =====================================================

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

csv_path = os.path.join(
    OUTPUT_FOLDER,
    "quelccaya_glacier_area_results.csv"
)

df.to_csv(csv_path, index=False)


# =====================================================
# 7. PLOT AREA CHANGE
# =====================================================

plt.figure(figsize=(10, 6))

plt.plot(
    df["year"],
    df["area_km2"],
    marker="o",
    linewidth=2
)

plt.xlabel("Year")
plt.ylabel("Estimated Glacier/Snow-Covered Area (km²)")
plt.title("Quelccaya Ice Cap: Glacier Surface Area Change (1990–2024)")
plt.grid(alpha=0.3)

loss = df["area_km2"].iloc[0] - df["area_km2"].iloc[-1]
total_percent_loss = (
    loss / df["area_km2"].iloc[0]
) * 100

plt.text(
    1992,
    df["area_km2"].max() - 5,
    f"Total loss: {loss:.1f} km² ({total_percent_loss:.1f}%)"
)

plt.tight_layout()

figure_path = os.path.join(
    OUTPUT_FOLDER,
    "quelccaya_glacier_area_change_clean.png"
)

plt.savefig(figure_path, dpi=300)
plt.show()


# =====================================================
# 8. EXPORT GLACIER MASK FRAMES
# =====================================================

def export_glacier_image(year, output_folder=FRAMES_FOLDER):
    os.makedirs(output_folder, exist_ok=True)

    glacier = create_glacier_mask(year)

    vis = glacier.visualize(
        min=0,
        max=1,
        palette=["000000", "00FFFF"]
    )

    url = vis.getThumbURL({
        "region": roi,
        "dimensions": 512,
        "format": "png"
    })

    response = requests.get(url)
    response.raise_for_status()

    filename = os.path.join(output_folder, f"glacier_{year}.png")

    with open(filename, "wb") as file:
        file.write(response.content)

    return filename


frame_files = []

for year in YEARS:
    print(f"Processing frame for {year}...")
    frame_file = export_glacier_image(year)
    frame_files.append(frame_file)


# =====================================================
# 9. CREATE GIF
# =====================================================

images = [imageio.imread(file) for file in frame_files]

gif_path = os.path.join(
    OUTPUT_FOLDER,
    "quelccaya_glacier_change.gif"
)

imageio.mimsave(
    gif_path,
    images,
    duration=3
)

print(f"CSV saved to: {csv_path}")
print(f"Figure saved to: {figure_path}")
print(f"GIF saved to: {gif_path}")
