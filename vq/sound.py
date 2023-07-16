from __future__ import annotations
from typing import *
from .utils import calculate_dbfs
import numpy as np
import logging

logger = logging.getLogger(__name__)

__all__ = [
  "Sound",
]

def cross_func(xs: np.ndarray) -> np.ndarray:
  return (xs + 1) / 2
  # return np.sqrt((xs + 1) / 2)

class Sound:
  def __init__(self, samples: np.ndarray) -> None:
    self.samples = samples
    if not (len(self.samples.shape) == 2):
      raise ValueError(f"Unrecognized samples dimension: {self.samples.shape}")
    if not (self.num_channels in {1, 2}):
      raise ValueError(f"Unrecognized samples #channels: {self.num_channels}")

  @property
  def num_channels(self) -> int:
    return self.samples.shape[0]

  @property
  def num_samples(self) -> int:
    return self.samples.shape[1]

  @property
  def dtype(self) -> np.dtype:
    return self.samples.dtype

  def __getitem__(self, ix) -> Sound:
    return Sound(self.samples[:,ix])

  def take(self, num_samples: int) -> Sound:
    return self[:num_samples]

  def drop(self, num_samples: int) -> Sound:
    return self[num_samples:]

  def __add__(self, other: Sound) -> Sound:
    return Sound.concatenate([self, other])

  def dbfs(self) -> float:
    return calculate_dbfs(self.samples)

  @staticmethod
  def concatenate(sounds: list[Sound]) -> Sound:
    concatenated_samples = np.concatenate([sound.samples for sound in sounds], axis=-1)
    return Sound(concatenated_samples)

  @staticmethod
  def allocate(
    *,
    num_channels: int,
    num_samples: int,
    dtype: np.dtype,
  ) -> Sound:
    samples = np.empty((num_channels, num_samples), dtype=dtype)
    return Sound(samples)