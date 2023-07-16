from __future__ import annotations

from .sound import Sound
from .source import Source
from .utils import audio_format_to_dtype
from dataclasses import dataclass
from typing import *
import av
import collections
import logging
import numpy as np

__all__ = [
  "Chunk",
  "Chunker",
]

logger = logging.getLogger(__name__)

@dataclass
class Chunk:
  video_frame: av.VideoFrame
  sound: Sound

  @property
  def time(self) -> float:
    return self.video_frame.time

class AudioBuffer:
  def __init__(self, source: Source) -> None:
    self.source = source # only here for extracting information
    self.buffer = Sound.allocate(
      num_channels = self.source.audio_stream.channels,
      num_samples  = 0,
      dtype        = audio_format_to_dtype(source.audio_stream.format),
    )
    self.got_first: bool = False
    self.pts_per_sample = 1.0 / (source.audio_stream.rate * source.audio_stream.time_base)
    self.current_pts: float = None 
    self._drop_until_pts: int = 0

  def send_frame(self, frame: av.AudioFrame) -> None:
    self.buffer = self.buffer + Sound(frame.to_ndarray())
    if not self.got_first:
      self.current_pts = frame.pts # set current_pts to that of the very first audio frame
      self.got_first = True
    self.consider_drop()

  def drop_until_pts(self, until_pts) -> None:
    assert self._drop_until_pts <= until_pts
    self._drop_until_pts = until_pts

  def consider_drop(self):
    want_to_drop = max(0, self._drop_until_pts - self.current_pts) / self.pts_per_sample
    curr_to_drop = int(min(want_to_drop, self.buffer.num_samples))
    self.receive_samples(curr_to_drop)

  def receive_samples(self, num_samples: int) -> Sound:
    read = self.buffer[:num_samples]
    self.buffer = self.buffer[num_samples:]
    self.current_pts += float(num_samples * self.pts_per_sample)
    return read

  def can_receive_samples(self, num_samples: int) -> bool:
    return num_samples <= self.buffer.num_samples

class VideoBuffer:
  def __init__(self, src: Source) -> None:
    self.src = src # only here for extracting information
    self.buffer: Deque[av.VideoFrame] = collections.deque()
    self.got_first = False

  def send_frame(self, frame: av.VideoFrame) -> None:
    self.buffer.append(frame)
    if not self.got_first:
      self.got_first = True

  def can_receive_one_frame(self) -> bool:
    return len(self.buffer) > 0

  def receive_one_frame(self) -> av.VideoFrame:
    return self.buffer.popleft()

class Chunker:
  def __init__(self, source: Source) -> None:
    self.source = source # only here for extracting information
    self.audio_buffer = AudioBuffer(source)
    self.video_buffer = VideoBuffer(source)
    self.aligning = True
    self.last_aread = 0
    self.avg_num_samples = source.audio_stream.rate / source.video_stream.average_rate

  def send_frame(self, frame: av.VideoFrame | av.AudioFrame) -> None:
    if isinstance(frame, av.VideoFrame):
      self.video_buffer.send_frame(frame)
    elif isinstance(frame, av.AudioFrame):
      self.audio_buffer.send_frame(frame)
    else:
      raise TypeError(f"Encountered unknown frame type: {type(frame)}, frame: {frame}")

  def receive_chunks(self) -> Generator[Chunk]:
    while True:
      if not self.video_buffer.can_receive_one_frame(): # video buffer has no frames to read
        break

      asamples = int(self.last_aread + self.avg_num_samples) - int(self.last_aread)
      if not self.audio_buffer.can_receive_samples(asamples): # audio buffer has insufficient sample count
        break

      v = self.video_buffer.receive_one_frame()
      a = self.audio_buffer.receive_samples(asamples)
      self.last_aread += self.avg_num_samples
      yield Chunk(video_frame=v, sound=a)

  def to_chunks(self, stream: Generator[av.VideoFrame | av.AudioFrame]) -> Generator[Chunk]:
    for frame in stream:
      self.send_frame(frame)
      yield from self.receive_chunks()

  """
  Return the (LIKELY) number of chunks that will be produced. Helpful for making progress bars.
  """
  @property
  def num_chunks(self) -> int:
    return self.source.num_vframes
