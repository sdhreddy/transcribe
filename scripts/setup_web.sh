#!/bin/bash
# Setup script for web development
python -m pip install -r requirements.txt
cd web/client && npm install
