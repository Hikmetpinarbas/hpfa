from __future__ import annotations
from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np

def _minute(ts_s: float) -> float:
    return ts_s / 60.0

def _bin_index(minute: float, bins):
    for i in range(len(bins)-1):
        if bins[i] <= minute < bins[i+