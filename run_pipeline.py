"""Root-level entry point so the pipeline can be run as `python run_pipeline.py`
from the project root, with no PYTHONPATH setup needed."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from run_pipeline import main

if __name__ == "__main__":
    main()
