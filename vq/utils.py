from __future__ import annotations
from typing import *
import datetime
import itertools
import av
import numpy as np
import re

def audio_format_to_dtype(format: av.AudioFormat) -> np.dtype:
  return av.audio.frame.format_dtypes[format.name]

def center_viewed(iterable, radius: int):
  window = []
  view_size = radius * 2 + 1
  for item in itertools.chain([None] * radius, iterable, [None] * radius):
    window.append(item)
    if len(window) == view_size:
      yield window
      window.pop(0)

def calculate_dbfs(samples: np.ndarray) -> float:
  with np.errstate(divide='ignore'):
    power = np.max(np.square(samples))
    return -np.inf if power == 0 else 10 * np.log10(power)
    # return 10 * np.log10(np.max(samples ** 2))

def format_time(total_seconds: float) -> str:
  h = int(total_seconds // 3600)
  m = int(total_seconds // 60) % 60
  s = total_seconds % 60
  return f"{h:02d}:{m:02d}:{s:06.3f}"

"""
parses 'HH:MM:SS.XXXXXX' where MM and SS are <60, but HH can be anything
"""
def parse_hhmmss(string: str) -> datetime.timedelta:
  result = re.match(r"^(\d+):(\d+):(\d+(?:\.\d+)?)$", string)
  if result is None:
    raise ValueError(f"cannot parse {string} as HH:MM:SS.NNNNNN format")
  else:
    hh, mm, ss = result.groups()
    hh = int(hh)
    mm = int(mm)
    ss = float(ss)
    if not (0 <= mm < 60):
      raise ValueError("minutes(={mm}) must be 0 <= x < 60")
    if not (0 <= ss < 60):
      raise ValueError("seconds(={ss}) must be 0 <= x < 60")
    return datetime.timedelta(hours=hh, minutes=mm, seconds=ss)