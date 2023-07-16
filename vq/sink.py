from __future__ import annotations
from typing import *
from .source import Source
from vq.sound import Sound
from dataclasses import dataclass
import av
import sys
import abc
import contextlib

__all__ = [
  "SinkError",
  "Sink",
  "Writer",
  "HandleWriter",
]

class SinkError(Exception):
  pass

class Sink:
  def __init__(
    self,
    *,
    container: av.OutputContainer,
    video_stream: av.VideoStream,
    audio_stream: av.AudioStream,
    ):
    self.container = container
    self.video_stream = video_stream
    self.audio_stream = audio_stream

  def enable_threading(self) -> None:
    self.video_stream.thread_type = "AUTO"
    self.audio_stream.thread_type = "AUTO"

  def write_sound(self, sound: Sound) -> None:
    assert isinstance(sound, Sound)
    frame = av.AudioFrame.from_ndarray(
      sound.samples,
      format=self.audio_stream.codec_context.format.name,
      layout=self.audio_stream.codec_context.layout.name
    )
    frame.rate = self.audio_stream.rate
    self.container.mux(self.audio_stream.encode(frame))

  def write_video_frame(self, frame: av.VideoFrame) -> None:
    assert isinstance(frame, av.VideoFrame)
    self.container.mux(self.video_stream.encode(frame))

class Writer(abc.ABC):
  @abc.abstractmethod
  @contextlib.contextmanager
  def open_like(self, source: Source) -> Iterator[Sink]:
    pass

class HandleWriter(Writer):
  STDOUT = sys.stdout.buffer
  def __init__(self, handle: BinaryIO, *, format: Optional[str] = None) -> None:
    self.handle = handle
    self.format = format

  @contextlib.contextmanager
  def open_like(self, source: Source) -> ContextManager[Sink]:
    container: av.OutputContainer = av.open(self.handle, format=self.format, mode="w")

    video_stream = container.add_stream(
      source.video_stream.codec_context.codec.name,
      rate   = source.video_stream.average_rate,
      width  = source.video_stream.width,
      height = source.video_stream.height,
      options = {
        "crf": "18", # Output high quality images
      }
    )
    audio_stream = container.add_stream(
      source.audio_stream.codec_context.codec.name,
      rate=source.audio_stream.rate,
      options = {
        "strict": "-2", # Enable support for experimental codecs like `opus`
      }
    )

    # FIXME: doing try/finally sometimes makes the program unkillable by Ctrl-C for some reason.
    # try:
    yield Sink(
      container = container,
      video_stream = video_stream,
      audio_stream = audio_stream,
    )

    # finally:
    #   container.close()
