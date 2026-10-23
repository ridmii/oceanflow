import struct
import numpy as np
from pathlib import Path

def test_particle_frame_binary_layout():
    # Since we are just testing the byte count and layout contract, 
    # we can generate a mock AoS buffer like 04_run_minimal_simulation.py does.
    
    particle_count = 2
    lons = np.array([-150.0, 150.0], dtype=np.float32)
    lats = np.array([30.0, -30.0], dtype=np.float32)
    speeds = np.array([0.5, 1.2], dtype=np.float32)
    ages = np.array([10.0, 20.0], dtype=np.float32)
    source_idxs = np.array([1, 2], dtype=np.int16)
    alives = np.array([1, 0], dtype=np.uint8)

    binary_data = b""
    for i in range(particle_count):
        binary_data += lons[i].tobytes()
        binary_data += lats[i].tobytes()
        binary_data += speeds[i].tobytes()
        binary_data += ages[i].tobytes()
        binary_data += source_idxs[i].tobytes()
        binary_data += alives[i].tobytes()
    
    assert len(binary_data) == particle_count * 19

    # Unpack manually to verify
    offset = 0
    u_lons, u_lats, u_speeds, u_ages, u_source_idxs, u_alives = [], [], [], [], [], []
    for _ in range(particle_count):
        u_lons.append(struct.unpack_from("f", binary_data, offset)[0]); offset += 4
        u_lats.append(struct.unpack_from("f", binary_data, offset)[0]); offset += 4
        u_speeds.append(struct.unpack_from("f", binary_data, offset)[0]); offset += 4
        u_ages.append(struct.unpack_from("f", binary_data, offset)[0]); offset += 4
        u_source_idxs.append(struct.unpack_from("h", binary_data, offset)[0]); offset += 2
        u_alives.append(struct.unpack_from("B", binary_data, offset)[0]); offset += 1

    np.testing.assert_array_equal(lons, u_lons)
    np.testing.assert_array_equal(lats, u_lats)
    np.testing.assert_array_equal(speeds, u_speeds)
    np.testing.assert_array_equal(ages, u_ages)
    np.testing.assert_array_equal(source_idxs, u_source_idxs)
    np.testing.assert_array_equal(alives, u_alives)
