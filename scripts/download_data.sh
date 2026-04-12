#!/bin/bash
echo "Downloading NASA SMAP/MSL dataset..."
pip install kaggle
kaggle datasets download -d patrickfleith/nasa-anomaly-detection-dataset-smap-msl
unzip nasa-anomaly-detection-dataset-smap-msl.zip -d Backend/data/
echo "Done."