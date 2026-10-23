FROM mambaorg/micromamba:1.5.8

USER root
WORKDIR /app

# Copy environment spec first for layer caching
COPY environment.yml .

# Install conda environment
RUN micromamba install -y -n base -f environment.yml && \
    micromamba clean --all --yes

# Make the conda env the default
ENV PATH=/opt/conda/bin:$PATH

# Now copy and install pip-only deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create /data directory for mounts
RUN mkdir -p /data

COPY src ./src
COPY scripts ./scripts
COPY config ./config

# Expose API port
EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
