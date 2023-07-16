from __future__ import annotations
from typing import *
from dataclasses import dataclass
import abc
import subprocess
import contextlib
import av
import io
import datetime

__all__ = [
  "SourceError",
  "Source",
  "Reader",
  "FileReader",
  "YtdlReader",
  "YtdlError",
  "YtdlProcessError",
]

class SourceError(Exception):
  pass

class Source:
  def __init__(
    self,
    *,
    container: av.InputContainer,
    video_stream: av.VideoStream,
    audio_stream: av.AudioStream
    ):
    self.container = container
    self.video_stream = video_stream
    self.audio_stream = audio_stream
    self._decoded: bool = False

  def enable_threading(self) -> None:
    self.video_stream.thread_type = "AUTO"
    self.audio_stream.thread_type = "AUTO"

  def decode(self) -> Generator[av.VideoFrame | av.AudioFrame]:
    # This function can only be called once
    #   self._decoded is used for keep track of that
    assert not self._decoded
    self._decoded = True
    return self.container.decode(self.audio_stream, self.video_stream)

  @staticmethod
  def from_container(container: av.InputContainer) -> Source:
    def pick_unique(stream_name, streams):
      if len(streams) == 0:
        raise SourceError(f"Opened container has no {stream_name} channel")
      if len(streams) > 1:
        raise SourceError(f"Opened container has multiple {stream_name} channel")
      return streams[0]

    return Source(
      container = container,
      audio_stream = pick_unique("audio", container.streams.audio),
      video_stream = pick_unique("video", container.streams.video),
    )


class Reader(abc.ABC):
  @abc.abstractmethod
  @contextlib.contextmanager
  def open(self) -> ContextManager[Source]:
    pass

class FileReader(Reader):
  def __init__(self, path: str) -> None:
    self.path = path

  @contextlib.contextmanager
  def open(self) -> ContextManager[Source]:
    container = av.open(self.path)
    try:
      yield Source.from_container(container)
    finally:
      container.close()

class YtdlError(Exception):
  pass

class YtdlProcessError(YtdlError):
  pass

class YtdlReader(Reader):
  def __init__(
    self,
    url: str,
    *,
    command = "yt-dlp",
  ) -> None:
    self.url = url
    self.command = command

  @contextlib.contextmanager
  def open(self) -> ContextManager[Source]:
    args = [
      self.command,
      "--quiet",
      "--output", "-", # output to stdout for subprocess.PIPE
      "--no-playlist", # avoid downloading the entire playlist if the video link includes the playlist id
      self.url,
    ]

    try:
      # Open process and capture stdout to read downloaded video data
      process = subprocess.Popen(args, stdout=subprocess.PIPE)
    except FileNotFoundError:
      raise YtdlProcessError(f"'{self.command}' command does not exist. Please install youtube-dl or verify that your PATH configuration is correct.")

    try:
      try:
        container = av.open(process.stdout)
        yield Source.from_container(container)
      except av.error.InvalidDataError:
        # it is possible that yt-dlp ends undesirably and prints out random information.
        outs, errs = process.communicate()
        raise YtdlProcessError(f"'{self.command}' command has exited unwantedly.") from None
    finally:
      process.terminate()