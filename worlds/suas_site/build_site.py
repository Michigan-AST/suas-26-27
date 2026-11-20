#!/usr/bin/env python3
"""Generate a consistent SUAS SITL world bundle for Gazebo, Foxglove, and evaluation.

Writes:
  - worlds/suas_site/scene.json          (single source of truth: origin, boundaries, targets, objects)
  - worlds/suas_site/dem.npz             (elevation grid in metres relative to site origin)
  - worlds/suas_site/ground_texture.png  (textured ground image for feature-rich stitching in Gazebo)
  - sim/gz/worlds/suas_site.sdf          (Gazebo Harmonic world referencing rc_cessna_cam_down)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parents[2]
WORLD_DIR = Path(__file__).resolve().parent
SDF_OUT = REPO_ROOT / "sim" / "gz" / "worlds" / "suas_site.sdf"


def default_scene(
    lat_deg: float = 47.397971057728974,
    lon_deg: float = 8.546163739800146,
    elevation_m: float = 0.0,
) -> dict[str, Any]:
    """Return the canonical SUAS SITL scene definition aligned with missions/mapping_sitl.json."""
    return {
        "name": "suas_site",
        "origin": {
            "latitude_deg": lat_deg,
            "longitude_deg": lon_deg,
            "elevation_m": elevation_m,
        },
        "search_boundary": {
            "min_north": 700.0,
            "max_north": 900.0,
            "min_east": 200.0,
            "max_east": 400.0,
            "buffer_m": 15.0,
        },
        "ground_patch": {
            "center_north": 800.0,
            "center_east": 300.0,
            "size_north_m": 320.0,
            "size_east_m": 320.0,
            "texture_file": "ground_texture.png",
        },
        "targets": [
            {
                "id": "tent_1",
                "label": "tent",
                "north_m": 760.0,
                "east_m": 265.0,
                "elevation_m": 0.0,
                "width_m": 3.0,
                "length_m": 3.0,
                "height_m": 2.4,
                "yaw_deg": 15.0,
            },
            {
                "id": "mannequin_1",
                "label": "mannequin",
                "north_m": 835.0,
                "east_m": 330.0,
                "elevation_m": 0.0,
                "width_m": 0.55,
                "length_m": 1.80,
                "height_m": 0.25,
                "yaw_deg": 35.0,
            },
        ],
        "objects": [
            # Trees around the search boundary (clear of direct target centers)
            {"id": "tree_1", "kind": "tree", "north_m": 725.0, "east_m": 230.0, "radius_m": 3.5, "height_m": 9.0},
            {"id": "tree_2", "kind": "tree", "north_m": 870.0, "east_m": 240.0, "radius_m": 4.0, "height_m": 10.0},
            {"id": "tree_3", "kind": "tree", "north_m": 848.0, "east_m": 342.0, "radius_m": 3.0, "height_m": 7.5},
            {"id": "tree_4", "kind": "tree", "north_m": 730.0, "east_m": 365.0, "radius_m": 3.8, "height_m": 8.5},
            {"id": "tree_5", "kind": "tree", "north_m": 880.0, "east_m": 370.0, "radius_m": 3.2, "height_m": 8.0},
            # Unrelated debris / vehicles (false-positive distractors per MAST-L2-PER-14)
            {"id": "truck_1", "kind": "vehicle", "north_m": 805.0, "east_m": 295.0, "length_m": 5.0, "width_m": 2.1, "height_m": 1.8, "yaw_deg": 20.0},
            {"id": "pallet_1", "kind": "debris", "north_m": 785.0, "east_m": 310.0, "length_m": 1.4, "width_m": 1.2, "height_m": 0.2, "yaw_deg": 10.0},
            {"id": "crate_1", "kind": "debris", "north_m": 815.0, "east_m": 250.0, "length_m": 1.2, "width_m": 0.9, "height_m": 0.6, "yaw_deg": 55.0},
            {"id": "tarp_grey", "kind": "debris", "north_m": 745.0, "east_m": 325.0, "length_m": 2.6, "width_m": 2.0, "height_m": 0.06, "yaw_deg": 70.0},
        ],
    }


def generate_ground_texture(out_path: Path, size_px: int = 1024, seed: int = 42) -> None:
    """Create a feature-rich aerial ground texture so feature-based stitchers have abundant keypoints."""
    rng = np.random.default_rng(seed)

    def smooth_noise(grid: int) -> np.ndarray:
        base = rng.random((grid, grid), dtype=np.float32)
        im = Image.fromarray(base).resize((size_px, size_px), Image.Resampling.BICUBIC)
        return np.clip(np.asarray(im, dtype=np.float32), 0.0, 1.0)

    n_macro = smooth_noise(12)
    n_med = smooth_noise(48)
    n_fine = smooth_noise(192)
    n_micro = rng.random((size_px, size_px), dtype=np.float32)

    field = np.clip(0.45 * n_macro + 0.30 * n_med + 0.15 * n_fine + 0.10 * n_micro, 0.0, 1.0)
    dry = np.clip((smooth_noise(16) - 0.52) * 3.0, 0.0, 1.0) * 0.65

    # Dry competition-field palette (sandy khaki / muted sage) — avoids video-game lawn green
    dark_field = np.array([108.0, 98.0, 72.0], dtype=np.float32)
    light_field = np.array([168.0, 154.0, 118.0], dtype=np.float32)
    dry_soil = np.array([178.0, 152.0, 112.0], dtype=np.float32)

    rgb = dark_field + (light_field - dark_field) * field[..., None]
    rgb += (dry_soil - rgb) * dry[..., None]

    # Subtle crop / mowing stripes for cross-pass matching features
    yy, xx = np.mgrid[0:size_px, 0:size_px]
    stripes = 6.0 * np.sin(xx * (2.0 * np.pi / 32.0))
    rgb = np.clip(rgb + stripes[..., None], 0.0, 255.0).astype(np.uint8)

    img = Image.fromarray(rgb)
    draw = ImageDraw.Draw(img)

    # Winding dirt service road + gravel pad + field path intersections (rich corners for SIFT/ORB)
    road_pts = [
        (int(size_px * (0.45 + 0.08 * np.sin(t * 2.2))), int(size_px * t))
        for t in np.linspace(0.0, 1.0, 25)
    ]
    draw.line(road_pts, fill=(148, 126, 98), width=22)
    draw.line([(x - 6, y) for x, y in road_pts], fill=(122, 102, 78), width=4)
    draw.line([(x + 6, y) for x, y in road_pts], fill=(122, 102, 78), width=4)

    cross_pts = [
        (int(size_px * t), int(size_px * (0.55 + 0.06 * np.cos(t * 3.0))))
        for t in np.linspace(0.0, 1.0, 20)
    ]
    draw.line(cross_pts, fill=(140, 122, 95), width=14)

    # Scattered rocks, dry bushes, soil patches, and gravel pads for dense unique local features
    for _ in range(180):
        cx = int(rng.integers(20, size_px - 20))
        cy = int(rng.integers(20, size_px - 20))
        rx = int(rng.integers(4, 18))
        ry = int(rng.integers(4, 18))
        tone = rng.choice(["bush", "soil", "stone", "hay"])
        if tone == "bush":
            col = (int(rng.integers(36, 64)), int(rng.integers(68, 102)), int(rng.integers(28, 48)))
        elif tone == "soil":
            col = (int(rng.integers(126, 160)), int(rng.integers(108, 136)), int(rng.integers(76, 102)))
        elif tone == "stone":
            v = int(rng.integers(135, 185))
            col = (v, v - 4, v - 8)
        else:
            col = (int(rng.integers(175, 205)), int(rng.integers(160, 188)), int(rng.integers(102, 128)))
        draw.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=col)

    img.save(out_path, format="PNG")


def generate_dem(
    out_path: Path,
    min_north: float = -100.0,
    max_north: float = 1100.0,
    min_east: float = -200.0,
    max_east: float = 600.0,
    step_m: float = 5.0,
    relief_m: float = 0.0,
) -> None:
    """Save a regular North/East elevation grid (.npz) relative to the site origin.

    Default relief_m=0.0 matches the flat Gazebo ground plane in suas_site.sdf so ground truth
    and simulated camera geometry agree exactly; pass --relief > 0 to synthesize sloped terrain.
    """
    north_axis = np.arange(min_north, max_north + step_m * 0.5, step_m, dtype=np.float32)
    east_axis = np.arange(min_east, max_east + step_m * 0.5, step_m, dtype=np.float32)
    nn, ee = np.meshgrid(north_axis, east_axis, indexing="ij")
    if relief_m > 0.0:
        elev = (
            relief_m * 0.5 * np.sin((nn - 700.0) / 80.0) * np.cos((ee - 200.0) / 90.0)
            + relief_m * 0.5 * np.clip((ee - 200.0) / 200.0, 0.0, 1.0)
        ).astype(np.float32)
    else:
        elev = np.zeros_like(nn, dtype=np.float32)

    np.savez_compressed(
        out_path,
        north_axis=north_axis,
        east_axis=east_axis,
        elevation_m=elev,
    )


def _tent_sdf(target: dict[str, Any]) -> str:
    """Open 4-leg blue pop-up canopy tent in Gazebo ENU (x=east, y=north, z=up)."""
    x = target["east_m"]
    y = target["north_m"]
    z = target.get("elevation_m", 0.0)
    w = target["width_m"]
    l = target["length_m"]
    h = target["height_m"]
    yaw_rad = np.radians(90.0 - target.get("yaw_deg", 0.0))
    half_x, half_y = w / 2.0 - 0.08, l / 2.0 - 0.08
    legs = []
    for idx, (lx, ly) in enumerate([(-half_x, -half_y), (half_x, -half_y), (half_x, half_y), (-half_x, half_y)]):
        legs.append(
            f"""        <visual name="leg_{idx}">
          <pose>{lx:.3f} {ly:.3f} {h / 2.0:.3f} 0 0 0</pose>
          <geometry><cylinder><radius>0.035</radius><length>{h:.3f}</length></cylinder></geometry>
          <material><ambient>0.85 0.85 0.85 1</ambient><diffuse>0.85 0.85 0.85 1</diffuse></material>
        </visual>"""
        )
    legs_xml = "\n".join(legs)
    return f"""    <model name="{target['id']}">
      <static>true</static>
      <pose>{x:.3f} {y:.3f} {z:.3f} 0 0 {yaw_rad:.6f}</pose>
      <link name="link">
{legs_xml}
        <visual name="canopy">
          <pose>0 0 {h:.3f} 0 0 0</pose>
          <geometry><box><size>{w:.3f} {l:.3f} 0.14</size></box></geometry>
          <material>
            <ambient>0.06 0.24 0.86 1</ambient>
            <diffuse>0.08 0.30 0.92 1</diffuse>
            <specular>0.15 0.15 0.2 1</specular>
          </material>
        </visual>
      </link>
    </model>"""


def _mannequin_sdf(target: dict[str, Any]) -> str:
    """Supine clothed mannequin in Gazebo ENU (x=east, y=north, z=up)."""
    x = target["east_m"]
    y = target["north_m"]
    z = target.get("elevation_m", 0.0)
    yaw_rad = np.radians(90.0 - target.get("yaw_deg", 0.0))
    return f"""    <model name="{target['id']}">
      <static>true</static>
      <pose>{x:.3f} {y:.3f} {z:.3f} 0 0 {yaw_rad:.6f}</pose>
      <link name="link">
        <visual name="torso">
          <pose>0.18 0 0.14 0 0 0</pose>
          <geometry><box><size>0.62 0.42 0.20</size></box></geometry>
          <material><ambient>0.88 0.18 0.08 1</ambient><diffuse>0.94 0.22 0.10 1</diffuse></material>
        </visual>
        <visual name="head">
          <pose>0.64 0 0.16 0 0 0</pose>
          <geometry><sphere><radius>0.13</radius></sphere></geometry>
          <material><ambient>0.85 0.68 0.56 1</ambient><diffuse>0.90 0.72 0.60 1</diffuse></material>
        </visual>
        <visual name="left_leg">
          <pose>-0.48 0.11 0.11 0 0 0</pose>
          <geometry><box><size>0.78 0.16 0.16</size></box></geometry>
          <material><ambient>0.18 0.24 0.42 1</ambient><diffuse>0.22 0.28 0.48 1</diffuse></material>
        </visual>
        <visual name="right_leg">
          <pose>-0.48 -0.11 0.11 0 0 0</pose>
          <geometry><box><size>0.78 0.16 0.16</size></box></geometry>
          <material><ambient>0.18 0.24 0.42 1</ambient><diffuse>0.22 0.28 0.48 1</diffuse></material>
        </visual>
        <visual name="arms">
          <pose>0.22 0 0.12 0 0 0</pose>
          <geometry><box><size>0.18 0.92 0.12</size></box></geometry>
          <material><ambient>0.88 0.18 0.08 1</ambient><diffuse>0.94 0.22 0.10 1</diffuse></material>
        </visual>
      </link>
    </model>"""


def _object_sdf(obj: dict[str, Any]) -> str:
    x = obj["east_m"]
    y = obj["north_m"]
    kind = obj["kind"]
    if kind == "tree":
        r = obj["radius_m"]
        h = obj["height_m"]
        trunk_h = h * 0.45
        return f"""    <model name="{obj['id']}">
      <static>true</static>
      <pose>{x:.3f} {y:.3f} 0 0 0 0</pose>
      <link name="link">
        <visual name="trunk">
          <pose>0 0 {trunk_h / 2.0:.3f} 0 0 0</pose>
          <geometry><cylinder><radius>0.30</radius><length>{trunk_h:.3f}</length></cylinder></geometry>
          <material><ambient>0.32 0.20 0.10 1</ambient><diffuse>0.36 0.22 0.12 1</diffuse></material>
        </visual>
        <visual name="canopy">
          <pose>0 0 {trunk_h + r * 0.65:.3f} 0 0 0</pose>
          <geometry><sphere><radius>{r:.3f}</radius></sphere></geometry>
          <material><ambient>0.14 0.32 0.12 1</ambient><diffuse>0.18 0.38 0.15 1</diffuse></material>
        </visual>
      </link>
    </model>"""

    l = obj["length_m"]
    w = obj["width_m"]
    h = obj["height_m"]
    yaw_rad = np.radians(90.0 - obj.get("yaw_deg", 0.0))
    if kind == "vehicle":
        col = "0.52 0.54 0.56 1"
    else:
        col = "0.55 0.48 0.36 1"
    return f"""    <model name="{obj['id']}">
      <static>true</static>
      <pose>{x:.3f} {y:.3f} {h / 2.0:.3f} 0 0 {yaw_rad:.6f}</pose>
      <link name="link">
        <visual name="box">
          <geometry><box><size>{l:.3f} {w:.3f} {h:.3f}</size></box></geometry>
          <material><ambient>{col}</ambient><diffuse>{col}</diffuse></material>
        </visual>
      </link>
    </model>"""


def build_sdf(scene: dict[str, Any], texture_rel_uri: str) -> str:
    """Build Gazebo Harmonic SDF world XML from scene.json."""
    origin = scene["origin"]
    patch = scene["ground_patch"]
    models = []
    for target in scene["targets"]:
        if target["label"] == "tent":
            models.append(_tent_sdf(target))
        elif target["label"] == "mannequin":
            models.append(_mannequin_sdf(target))
    for obj in scene["objects"]:
        models.append(_object_sdf(obj))
    models_xml = "\n".join(models)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!-- Auto-generated from worlds/suas_site/scene.json by worlds/suas_site/build_site.py -->
<sdf version="1.9">
  <world name="{scene['name']}">
    <physics type="ode">
      <max_step_size>0.004</max_step_size>
      <real_time_factor>1.0</real_time_factor>
      <real_time_update_rate>250</real_time_update_rate>
    </physics>
    <gravity>0 0 -9.8</gravity>
    <magnetic_field>6e-06 2.3e-05 -4.2e-05</magnetic_field>
    <atmosphere type="adiabatic"/>
    <scene>
      <grid>false</grid>
      <ambient>0.48 0.48 0.48 1</ambient>
      <background>0.68 0.78 0.90 1</background>
      <shadows>true</shadows>
    </scene>

    <light name="sunUTC" type="directional">
      <pose>0 0 500 0 0 0</pose>
      <cast_shadows>true</cast_shadows>
      <intensity>1.1</intensity>
      <direction>-0.35 0.45 -0.82</direction>
      <diffuse>0.95 0.94 0.90 1</diffuse>
      <specular>0.25 0.25 0.25 1</specular>
      <attenuation>
        <range>3000</range>
        <linear>0</linear>
        <constant>1</constant>
        <quadratic>0</quadratic>
      </attenuation>
    </light>

    <spherical_coordinates>
      <surface_model>EARTH_WGS84</surface_model>
      <world_frame_orientation>ENU</world_frame_orientation>
      <latitude_deg>{origin['latitude_deg']}</latitude_deg>
      <longitude_deg>{origin['longitude_deg']}</longitude_deg>
      <elevation>{origin['elevation_m']}</elevation>
    </spherical_coordinates>

    <!-- Infinite collision ground plane + runway visual at origin -->
    <model name="ground_plane">
      <static>true</static>
      <link name="link">
        <collision name="collision">
          <geometry><plane><normal>0 0 1</normal><size>4000 4000</size></plane></geometry>
          <surface><friction><ode/></friction></surface>
        </collision>
        <visual name="base_grass">
          <geometry><plane><normal>0 0 1</normal><size>3000 3000</size></plane></geometry>
          <material>
            <ambient>0.42 0.38 0.28 1</ambient>
            <diffuse>0.52 0.46 0.34 1</diffuse>
          </material>
        </visual>
        <visual name="runway">
          <pose>0 0 0.01 0 0 0</pose>
          <geometry><box><size>14 160 0.02</size></box></geometry>
          <material>
            <ambient>0.24 0.24 0.26 1</ambient>
            <diffuse>0.28 0.28 0.30 1</diffuse>
          </material>
        </visual>
      </link>
    </model>

    <!-- High-texture Search Boundary ground patch for stitching & feature matching -->
    <model name="survey_ground_patch">
      <static>true</static>
      <pose>{patch['center_east']:.3f} {patch['center_north']:.3f} 0.02 0 0 0</pose>
      <link name="link">
        <visual name="textured_patch">
          <geometry>
            <box><size>{patch['size_east_m']:.3f} {patch['size_north_m']:.3f} 0.02</size></box>
          </geometry>
          <material>
            <ambient>0.85 0.85 0.85 1</ambient>
            <diffuse>0.95 0.95 0.95 1</diffuse>
            <specular>0.05 0.05 0.05 1</specular>
            <pbr>
              <metal>
                <albedo_map>{texture_rel_uri}</albedo_map>
                <roughness>0.92</roughness>
                <metalness>0.0</metalness>
              </metal>
            </pbr>
          </material>
        </visual>
      </link>
    </model>

    <!-- Aircraft with fixed downward 2 Hz nadir mapping camera (attached by PX4 via PX4_GZ_MODEL_NAME=rc_cessna_0) -->
    <include>
      <uri>model://rc_cessna_cam_down</uri>
      <name>rc_cessna_0</name>
      <pose>0 0 0.25 0 0 1.57079632679</pose>
    </include>

{models_xml}
  </world>
</sdf>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Build SUAS SITL world bundle (scene.json, DEM, texture, Gazebo SDF).")
    parser.add_argument("--lat", type=float, default=47.397971057728974, help="Site origin latitude (deg)")
    parser.add_argument("--lon", type=float, default=8.546163739800146, help="Site origin longitude (deg)")
    parser.add_argument("--alt", type=float, default=0.0, help="Site origin elevation AMSL (m)")
    parser.add_argument("--relief", type=float, default=0.0, help="Optional synthetic DEM relief amplitude (m)")
    parser.add_argument("--texture-size", type=int, default=1024, help="Ground texture resolution in px")
    args = parser.parse_args()

    WORLD_DIR.mkdir(parents=True, exist_ok=True)
    SDF_OUT.parent.mkdir(parents=True, exist_ok=True)

    scene = default_scene(lat_deg=args.lat, lon_deg=args.lon, elevation_m=args.alt)
    scene_path = WORLD_DIR / "scene.json"
    scene_path.write_text(json.dumps(scene, indent=2) + "\n", encoding="utf-8")

    tex_path = WORLD_DIR / scene["ground_patch"]["texture_file"]
    generate_ground_texture(tex_path, size_px=args.texture_size)

    dem_path = WORLD_DIR / "dem.npz"
    generate_dem(dem_path, relief_m=args.relief)

    # Gazebo resolves relative texture paths from the directory containing the .sdf file
    sdf_text = build_sdf(scene, texture_rel_uri="../../../worlds/suas_site/ground_texture.png")
    SDF_OUT.write_text(sdf_text, encoding="utf-8")

    print(f"Wrote {scene_path}")
    print(f"Wrote {tex_path}")
    print(f"Wrote {dem_path}")
    print(f"Wrote {SDF_OUT}")


if __name__ == "__main__":
    main()
