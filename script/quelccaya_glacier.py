# =====================================================
# PROJECT: Quelccaya Ice Cap (Peru) Glacier Surface Area Change Detection
# AUTHOR: David A. Olaechea Dongo
# DESCRIPTION:
# Quantify long-term glacier surface area change at the Quelccaya Ice Cap (Peru)
# using Landsat satellite imagery and Google Earth Engine from 1990 to 2024. 
# =====================================================

import os
import requests
import imageio.v2 as imageio

import ee
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from PIL import Image
from io import BytesIO
from matplotlib.patches import Rectangle

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
# 7. CREATE VISUAL OUTPUTS
# =====================================================

def get_true_color_with_glacier_overlay(year):
    image = get_landsat_collection(year).median().clip(roi)

    if year < 2013:
        rgb_bands = ["SR_B3", "SR_B2", "SR_B1"]  # Landsat 5/7 true color
    else:
        rgb_bands = ["SR_B4", "SR_B3", "SR_B2"]  # Landsat 8 true color

    glacier = create_glacier_mask(year).selfMask()

    true_color = image.visualize(
        bands=rgb_bands,
        min=0.02,
        max=0.35,
        gamma=1.2
    )

    glacier_overlay = glacier.visualize(
        palette=["00FFFF"],
        opacity=0.6
    )

    combined = true_color.blend(glacier_overlay)

    url = combined.getThumbURL({
        "region": roi,
        "dimensions": 900,
        "format": "png"
    })

    response = requests.get(url)
    response.raise_for_status()

    return Image.open(BytesIO(response.content))


def add_map_elements(ax, label_text="Detected glacier/snow-covered area"):
    # Coordinate grid
    lon_min, lon_max = -70.90, -70.70
    lat_min, lat_max = -14.00, -13.83

    height, width = ax.images[0].get_array().shape[:2]

    ax.set_xlim(0, width)
    ax.set_ylim(height, 0)

    lon_ticks = np.linspace(lon_min, lon_max, 5)
    lat_ticks = np.linspace(lat_min, lat_max, 5)

    x_ticks = np.linspace(0, width, 5)
    y_ticks = np.linspace(height, 0, 5)

    ax.set_xticks(x_ticks)
    ax.set_yticks(y_ticks)

    ax.set_xticklabels([f"{abs(lon):.2f}°W" for lon in lon_ticks], fontsize=8)
    ax.set_yticklabels([f"{abs(lat):.2f}°S" for lat in lat_ticks], fontsize=8)

    ax.grid(color="white", linestyle="--", linewidth=0.6, alpha=0.7)

    # Legend box
    legend_x = 0.04
    legend_y = 0.05
    legend_size = 0.05

    legend_patch = Rectangle(
        (legend_x, legend_y),
        legend_size,
        legend_size,
        transform=ax.transAxes,
        facecolor="#00FFFF",
        edgecolor="black"
    )
    ax.add_patch(legend_patch)

    ax.text(
        legend_x + legend_size + 0.015,
        legend_y + legend_size / 2,
        label_text,
        transform=ax.transAxes,
        fontsize=9,
        va="center",
        ha="left",
        bbox=dict(facecolor="white", alpha=0.8, edgecolor="none")
    )
    # North arrow
    ax.annotate(
        "N",
        xy=(0.92, 0.88),
        xytext=(0.92, 0.72),
        xycoords="axes fraction",
        arrowprops=dict(facecolor="black", width=4, headwidth=12),
        ha="center",
        va="center",
        fontsize=12,
        fontweight="bold"
    )

    # Scale bar
    ax.plot(
        [0.08, 0.28],
        [0.92, 0.92],
        transform=ax.transAxes,
        color="black",
        linewidth=4
    )

    ax.text(
        0.18, 0.89,
        "~5 km",
        transform=ax.transAxes,
        ha="center",
        fontsize=9,
        bbox=dict(facecolor="white", alpha=0.8, edgecolor="none")
    )

    ax.margins(0)

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

img_1990 = get_true_color_with_glacier_overlay(1990)
img_2024 = get_true_color_with_glacier_overlay(2024)

fig, axes = plt.subplots(1, 2, figsize=(14, 7))

axes[0].imshow(img_1990)
axes[0].set_title("1990")
add_map_elements(axes[0])

axes[1].imshow(img_2024)
axes[1].set_title("2024")
add_map_elements(axes[1])

plt.suptitle("Quelccaya Ice Cap: True Color Satellite Image with Glacier Mask Overlay")

plt.tight_layout()

plt.subplots_adjust(bottom=0.05)

before_after_path = os.path.join(
    OUTPUT_FOLDER,
    "quelccaya_before_after_true_color.png"
)

plt.savefig(before_after_path, dpi=300)

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
    duration=5
)

print(f"CSV saved to: {csv_path}")
print(f"Figure saved to: {figure_path}")
print(f"GIF saved to: {gif_path}")
print(f"Before/after figure saved to: {before_after_path}")
