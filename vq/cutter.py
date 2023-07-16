from __future__ import annotations

from typing import *
from .sound import *
from .chunker import *
from .source import *
from .utils import center_viewed
from dataclasses import dataclass
import av
import collections
import logging
import math

__all__ = [
  "CutChunk",
  "Cutter",
]

logger = logging.getLogger(__name__)

@dataclass
class CutChunk:
  video_frame: av.VideoFrame
  sound: Sound
  dbfs: float
  prev_cut_duration: Optional[float] = None # Additional information

  @property
  def time(self) -> float:
    return self.video_frame.time

class Cutter:
  def __init__(
    self,
    source: Source,
    *,
    tolerance: float,
    after_loud_save_duration: float
  ) -> None:
    """
    :param tolerance: Threshold (in dBFS) defining the boundary between a loud chunk and a silent chunk
    :param after_loud_save_duration: Do not skip a silent chunk if between it and the most recent loud chunk is less than this amount of seconds
    """
    self.source = source
    self.tolerance = tolerance
    self.after_loud_save_duration = after_loud_save_duration

  def cut_chunks(self, chunks: Generator[Chunk]) -> Generator[CutChunk]:
    last_loud_t = -math.inf # Initialized to math.inf because it makes the programming logic more convenient
    last_total_skip_t = 0

    for chunk in chunks:
      cut_chunk = CutChunk(
        video_frame = chunk.video_frame,
        sound       = chunk.sound,
        dbfs        = chunk.sound.dbfs(),
        )
      is_silent = cut_chunk.dbfs < self.tolerance
      if is_silent:
        # `cut_chunk` is silent
        if cut_chunk.time - last_loud_t <= self.after_loud_save_duration:
          # Within `after_loud_save_duration`, accept this silent chunk
          yield cut_chunk
        else:
          last_total_skip_t += 1.0 / self.source.video_stream.average_rate
          pass # Skip this chunk
      else:
        # `cut_chunk` is loud
        # Update state
        last_loud_t = cut_chunk.time
        if last_total_skip_t > 0:
          cut_chunk.prev_cut_duration = last_total_skip_t
          last_total_skip_t = 0
        yield cut_chunk