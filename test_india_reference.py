import os
import sys

# Ensure step_esg_pipeline is on sys.path
pipeline_dir = os.path.join(os.path.dirname(__file__), "step_esg_pipeline")
if pipeline_dir not in sys.path:
    sys.path.insert(0, pipeline_dir)

from test_india_reference import test_india_excel_integration

if __name__ == "__main__":
    success = test_india_excel_integration()
    sys.exit(0 if success else 1)
