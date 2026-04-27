#!/bin/bash
# Docker entrypoint script to patch perth module before running the app

# Patch perth module to use DummyWatermarker for PerthImplicitWatermarker
python3 -c "
import perth
import sys

# Patch PerthImplicitWatermarker if it's None
if perth.PerthImplicitWatermarker is None:
    print('Patching perth.PerthImplicitWatermarker with DummyWatermarker')
    perth.PerthImplicitWatermarker = perth.DummyWatermarker
    # Update the module in sys.modules
    sys.modules['perth'] = perth
"

# Run the main application
exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8000