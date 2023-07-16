from __future__ import annotations
from typing import *

from .source import *
from .sink import *
from .chunker import *
from .cutter import *

import av
import numpy as np

__all__ = [
  "RgbFrame",
  "VideoFrameModifier",
  "cut",
  "CutChunk", # re-export
]

RgbFrame = np.ndarray
VideoFrameModifier = Callable[[CutChunk, RgbFrame], RgbFrame]

def cut(
  source: Source,
  sink: Sink,
  tolerance: float,
  after_loud_save_duration: float,
  video_frame_modifier: Optional[VideoFrameModifier] = None
  ) -> None:
  chunker = Chunker(source)
  cutter = Cutter(
    source,
    tolerance = tolerance,
    after_loud_save_duration = after_loud_save_duration
    )

  cut_chunk_stream = cutter.cut_chunks(chunker.to_chunks(source.decode()))
  for cut_chunk in cut_chunk_stream:
    sound = cut_chunk.sound
    video_frame = cut_chunk.video_frame
    if video_frame_modifier is not None:
      ndframe = video_frame.to_rgb().to_ndarray()
      ndframe = video_frame_modifier(cut_chunk, ndframe)
      video_frame = av.VideoFrame.from_ndarray(ndframe, format="rgb24")
    else:
      # to ndarray and go back creating a new VideoFrame to reset the pts or something idk
      ndframe = video_frame.to_ndarray()
      video_frame = av.VideoFrame.from_ndarray(ndframe, format=video_frame.format.name)
    sink.write_sound(sound)
    sink.write_video_frame(video_frame)
