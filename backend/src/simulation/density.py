"""
src/simulation/density.py
=========================
Density frame computation.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter

def compute_density_frame(
    lon: np.ndarray,          
    lat: np.ndarray,          
    alive: np.ndarray,        
    bounds: dict,             
    cols: int,                
    rows: int,                
    blur_sigma: float = 0.8,
) -> np.ndarray:
    """
    Bin live particle positions into a (rows, cols) grid, apply a light
    Gaussian blur, and normalize to [0, 1].

    Returns a float32 array of shape (rows, cols), C-contiguous.
    """
    west = bounds["west"]
    east = bounds["east"]
    south = bounds["south"]
    north = bounds["north"]

    if west > east:
        raise ValueError("Bounds crossing antimeridian not supported.")

    valid_mask = (
        (alive != 0) &
        (lon >= west) & (lon <= east) &
        (lat >= south) & (lat <= north)
    )

    valid_lon = lon[valid_mask]
    valid_lat = lat[valid_mask]

    if len(valid_lon) == 0:
        return np.zeros((rows, cols), dtype=np.float32)

    lon_edges = np.linspace(west, east, cols + 1)
    lat_edges_asc = np.linspace(south, north, rows + 1)

    H, _, _ = np.histogram2d(
        valid_lat, valid_lon, 
        bins=[lat_edges_asc, lon_edges]
    )

    H = np.flipud(H)

    if blur_sigma > 0:
        H_blurred = gaussian_filter(H, sigma=blur_sigma, mode="constant", cval=0.0)
    else:
        H_blurred = H

    max_val = np.max(H_blurred)
    if max_val > 0:
        H_normalized = H_blurred / max_val
    else:
        H_normalized = H_blurred

    return np.ascontiguousarray(H_normalized, dtype=np.float32)
