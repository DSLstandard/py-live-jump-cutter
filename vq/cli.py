from __future__ import annotations

from .sink import HandleWriter
from .source import Reader, FileReader, YtdlReader, Source
from .utils import format_time, parse_hhmmss
from typing import *
import argparse
import av
import cv2
import datetime
import io
import logging
import math
import subprocess
import sys
import tqdm
import vq

logger = logging.getLogger(__name__)

LOG_LEVELS = {
  "debug": logging.DEBUG,
  "info": logging.INFO,
  "error": logging.ERROR,
}

def parse_command_line() -> argparse.Namespace:
  parser = argparse.ArgumentParser(
      "vq",
      formatter_class=argparse.ArgumentDefaultsHelpFormatter
      )
  parser.add_argument(
      "-v", "--log-level",
      choices=LOG_LEVELS.keys(), type=lambda x: LOG_LEVELS[x],
      default=logging.INFO,
      help="Set the log level")
  parser.add_argument(
      "-t", "--tolerance",
      type=float, default=-20.0,
      help="Set the tolerance level (in dBFS)."
      )
  parser.add_argument(
      "-m", "--after-loud-save-duration",
      type=float, default=0.3,
      help="Do not skip a silent chunk if between it and the most recent loud chunk is less than this amount of seconds")
  parser.add_argument(
      "-f", "--output-format",
      type=str, default=None,
      help="Destination container format, defaults to 'matroska' if dest is - (stdout).")
  parser.add_argument(
      "-z", "--font-scale",
      type=float, default=0.4,
      help="Specify the scale of the font used in --draw-info")
  parser.add_argument(
      "-i", "--draw-info",
      action="store_true",
      help="Draw info at the bottom of the video?"
      )
  parser.add_argument(
      "input",
      type=str,
      help="Set the source of the input (can either be a file path, or a YouTube url).")
  parser.add_argument(
      "output",
      type=str, nargs="?", default="-",
      help="Set the output (can either be a file path, or '-' for stdout).")
  return parser.parse_args()

def make_reader(args: argparse.Namespace) -> Reader:
  if args.input.startswith("https://"):
    # also handles the '-F -' logic
    logger.info(f"detected source input as from YouTube url {args.input}")
    return YtdlReader(args.input)
  else:
    logger.info(f"detected source input as file input")
    return FileReader(args.input)

def make_writer(args: argparse.Namespace) -> Writer:
  format: str = args.output_format
  if args.output == "-":
    # Output is stdout
    if format is None:
      format = "matroska"
      logger.info(f"output format defaulted to {format} as destination is - (stdout)")
    handle = sys.stdout.buffer
  else:
    # Output is (probably) a file
    handle = io.open(args.output, "wb")
  return HandleWriter(handle, format=format)

class InfoDrawer:
  def __init__(self, source: Source, args: argparse.Namespace):
    # For information
    self.args = args
    self.source = source
    # Statistics
    self.total_cut_duration: float = 0
    self.last_cut_time: float = None
    self.last_cut_duration: float = 0

  def on_callback(self, cut_chunk: vq.CutChunk, frame: vq.RgbFrame) -> vq.RgbFrame:
    # Update statistics
    if cut_chunk.prev_cut_duration is not None:
      self.total_cut_duration += cut_chunk.prev_cut_duration
      self.last_cut_duration = cut_chunk.prev_cut_duration
      self.last_cut_time = cut_chunk.time

    # Draw on frame
    frame_height, frame_width, _ = frame.shape

    def draw_line(at_line: int, string: str, color) -> Noen:
      bottom_pad = 5 * self.args.font_scale
      line_height = 25 * self.args.font_scale
      y = int(frame_height - bottom_pad - (bottom_pad + line_height) * at_line)
      cv2.putText(frame, string, (0, y), cv2.FONT_HERSHEY_SIMPLEX, self.args.font_scale, (0, 0, 0), 2)
      cv2.putText(frame, string, (0, y), cv2.FONT_HERSHEY_SIMPLEX, self.args.font_scale, color)

    # Draw realtime info
    realtime = format_time(cut_chunk.time)
    totalcut = format_time(self.total_cut_duration)
    draw_line(0, f"realtime={realtime}", (255, 255, 255))

    # brightness calculation
    factor = 0.05
    bright = factor ** (cut_chunk.time - (self.last_cut_time or -math.inf))

    # Draw totalcut info
    cut_percent = self.total_cut_duration/(cut_chunk.time + 1/self.source.video_stream.average_rate)*100
    draw_line(1, f"totalcut={totalcut}[{cut_percent:.03f}%]", (255 * (1-bright), 255, 255))

    # Draw recent cut info
    text: str
    if self.last_cut_time is None:
      text = f"[never cut]"
    else:
      text = f"[cut +{format_time(self.last_cut_duration)}@{format_time(self.last_cut_time)}]"
    draw_line(2, text, (0, 255*bright, 255*bright))

    # Draw dBFS info, and the color shall be reflective of how loud it is with respect to the specified tolerance level
    max_diff = 20
    diff  = min(max_diff, cut_chunk.dbfs - self.args.tolerance)
    red   = min(0xFF, 0xFF * 2 * (1 - diff / max_diff))
    green = min(0xFF, 0xFF * 2 * diff / max_diff)
    draw_line(3, f"tolerance={self.args.tolerance}<dBFS={cut_chunk.dbfs:.2f}", (red, green, 0))
    return frame


def main():
  args = parse_command_line()

  logging.basicConfig(
    stream=sys.stderr,
    level=args.log_level,
  )

  reader = make_reader(args)
  writer = make_writer(args)

  try:
    with reader.open() as source, writer.open_like(source) as sink:
      drawer = None
      if args.draw_info:
        drawer = InfoDrawer(source, args)
        vq.cut(source, sink, args.tolerance, args.after_loud_save_duration, drawer.on_callback)
      else:
        vq.cut(source, sink, args.tolerance, args.after_loud_save_duration)
  except BrokenPipeError as e:
    logger.error(f"Pipe broken! {e}")
  except KeyboardInterrupt:
    pass
