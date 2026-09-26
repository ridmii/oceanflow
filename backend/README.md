# OceanFlow — Backend Scaffold

Python environment setup for the Ocean Plastic Transport Tracker simulation backend.

> **Scope of this scaffold:** Environment setup, credential management, dataset discovery, and test data download. The FastAPI server, Celery worker, and Parcels/PlasticParcels simulation are **not yet built**. Come back with a validated dataset ID and a working test download, and the next phase will begin.

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | **3.11** | Required. 3.10 or 3.12 may work but are untested. |
| conda **or** pip/venv | Any recent | Pick one path below. |
| Internet access | — | Needed to fetch catalogue and data. |
| Copernicus Marine account | Free | Register at https://data.marine.copernicus.eu/register |

---

## Setup — Option A: conda (recommended)

```bash
cd backend

# 1. Create the environment (downloads all packages)
conda env create -f environment.yml

# 2. Activate it
conda activate copernicus-env

# 3. Install pip-only packages (copernicusmarine, parcels, plasticparcels)
#    These are listed in the pip: section of environment.yml and are installed
#    automatically by conda, but re-running this is harmless.
pip install -r requirements.txt
```

> **Note on Parcels versions:** `requirements.txt` pins `parcels==3.0.5` and
> `plasticparcels==0.4.0`. If you need `parcels` 4.x (e.g., for unstructured
> grid support), you must also upgrade `plasticparcels` to ≥ 0.5.0 and rewrite
> any simulation code accordingly. See [Known Unknowns](#known-unknowns).

---

## Setup — Option B: venv

```bash
cd backend

# 1. Create a Python 3.11 virtual environment
python3.11 -m venv .venv

# 2. Activate it
# macOS / Linux:
source .venv/bin/activate
# Windows (PowerShell):
.venv\Scripts\Activate.ps1

# 3. Install all dependencies
pip install -r requirements.txt
```

---

## Configure Credentials

```bash
# Copy the example file
cp .env.example .env

# Open .env in your editor and fill in your credentials
# (or leave them blank and use `copernicusmarine login` below)
```

`backend/.env` is listed in `.gitignore` and will never be committed.

---

## Log in to Copernicus Marine

The copernicusmarine toolbox can authenticate two ways:

**Option 1 — cached token (preferred):**
```bash
copernicusmarine login
# Follow the prompts. Token is saved to ~/.copernicusmarine/
# You only need to do this once per machine (token lasts ~30 days).
```

**Option 2 — credentials in .env:**
```bash
# Set in backend/.env:
COPERNICUS_USERNAME=your_email@example.com
COPERNICUS_PASSWORD=yourpassword
```

Both options are supported by all scripts.

---

## Scripts

Run all scripts from the `backend/` directory with the environment activated.

### 1. Test the connection

```bash
python scripts/test_connection.py
```

Calls the Copernicus Marine catalogue API (metadata only, no download).
Prints `[OK] Connection successful` or a diagnosis of what went wrong.

---

### 2. Discover dataset IDs

```bash
python scripts/discover_datasets.py

# Filter a different product:
python scripts/discover_datasets.py --product GLOBAL_ANALYSISFORECAST_PHY_001_024
```

Queries the catalogue for all datasets in the Global Ocean Physics product,
highlights those with `uo` and `vo` surface current variables, and prints
a ready-to-paste `copernicusmarine subset` command.

> ⚠ Always verify your chosen dataset in the **MyOcean Pro viewer** before
> downloading: https://data.marine.copernicus.eu/viewer/expert

After choosing a dataset, add its ID to `backend/.env`:

```
COPERNICUS_DATASET_ID=cmems_mod_glo_phy_anfc_0.083deg_P1D-m
```

---

### 3. Download a test subset

```bash
python scripts/download_test_subset.py
```

Downloads a small surface-current subset (uo + vo, surface layer, ≤ 7 days)
using `copernicusmarine.subset()`. Safety guards prevent accidentally
downloading large datasets.

Saved to: `backend/data/test/test_currents.nc`

You can override parameters on the command line:

```bash
python scripts/download_test_subset.py \
    --west -160 --east -120 --south 20 --north 50 \
    --start 2024-01-01 --end 2024-01-02
```

---

### 4. Inspect the downloaded file

```bash
python scripts/inspect_download.py data/test/test_currents.nc
```

Prints dimensions, variable statistics, coordinate ranges, and NaN counts.
Saves a quiver plot to `backend/data/test/inspect_plot.png`.
Outputs a final verdict: **LOOKS VALID** or a list of problems.

---

## Find a Dataset ID (Manual Step)

1. Run `python scripts/discover_datasets.py` — it will suggest a dataset ID.
2. Cross-check at **https://data.marine.copernicus.eu/viewer/expert**:
   - Search for product `GLOBAL_ANALYSISFORECAST_PHY_001_024`.
   - Verify `uo` and `vo` are listed as available variables.
   - Check the temporal and spatial extent covers your region of interest.
3. Set `COPERNICUS_DATASET_ID=<your-dataset-id>` in `backend/.env`.

---

## Project Structure

```
backend/
├── .env.example          # Template — copy to .env and fill in
├── .env                  # Your credentials (gitignored)
├── .gitignore
├── environment.yml       # conda environment definition
├── requirements.txt      # pip requirements (Python 3.11)
├── README.md
├── config/
│   ├── simulation.yaml   # Simulation parameters (region, time, particles)
│   └── sources.csv       # 20 river sources (Meijer et al. 2021)
├── scripts/
│   ├── test_connection.py       # Verify Copernicus Marine is reachable
│   ├── discover_datasets.py     # Browse catalogue, find dataset ID
│   ├── download_test_subset.py  # Download small test subset
│   └── inspect_download.py      # Validate + plot downloaded NetCDF
├── src/
│   ├── __init__.py
│   ├── data/
│   │   ├── __init__.py
│   │   └── copernicus_client.py  # Credential loader, config validator
│   └── utils/
│       ├── __init__.py
│       └── paths.py               # PROJECT_ROOT, DATA_DIR, run helpers
├── data/                  # Downloaded data (gitignored)
│   └── .gitkeep
└── notebooks/             # Jupyter exploration notebooks (gitignored)
    └── .gitkeep
```

---

## Full Quickstart (copy-paste order)

```bash
# ── 1. Setup (conda path) ─────────────────────────────────────────
cd backend
conda env create -f environment.yml
conda activate copernicus-env

# ── 2. Configure credentials ──────────────────────────────────────
cp .env.example .env
# Edit .env with your credentials, OR use login below

# ── 3. Log in ─────────────────────────────────────────────────────
copernicusmarine login

# ── 4. Verify connection ──────────────────────────────────────────
python scripts/test_connection.py

# ── 5. Find your dataset ID ───────────────────────────────────────
python scripts/discover_datasets.py
# → Edit backend/.env: COPERNICUS_DATASET_ID=<chosen-id>

# ── 6. Download a test subset ─────────────────────────────────────
python scripts/download_test_subset.py

# ── 7. Inspect the download ───────────────────────────────────────
python scripts/inspect_download.py data/test/test_currents.nc
```

---

## Known Unknowns

| Unknown | Impact | How to resolve |
|---|---|---|
| **Parcels v3 vs v4 API** | `parcels` 4.x has a substantially different API than 3.x. `plasticparcels 0.4.0` is the last release supporting v3. Future `plasticparcels` versions will require v4. | Pin as in `requirements.txt`; verify with `pip show parcels plasticparcels` after install. |
| **Exact dataset ID** | Cannot be determined without authenticating. Different dataset IDs cover different resolutions and time frequencies (daily, hourly). | Run `python scripts/discover_datasets.py` after login. |
| **Dataset availability window** | The Analysis & Forecast product typically provides ~10 days of forecast and a multi-year reanalysis. The right dataset ID depends on whether you want real-time or historical data. | Check temporal coverage in discover output and MyOcean viewer. |
| **`copernicusmarine.describe()` response schema** | The JSON schema of `describe()` changes between toolbox releases. `discover_datasets.py` uses defensive `dict.get()` calls throughout. | If discover fails, upgrade: `pip install --upgrade copernicusmarine`. |
| **PlasticParcels coastline data** | `plasticparcels` requires a global coastline/bathymetry dataset for beaching. It is not downloaded here. | Will be addressed in the simulation phase. |

---

## Credentials Security

- **Never** hardcode credentials in Python files.
- `backend/.env` is in `.gitignore` — it will not be committed.
- The `copernicusmarine login` token is cached in `~/.copernicusmarine/` (your home directory) and is also never committed.
- If you must share this repo, double-check with `git status` that `.env` is not staged.
