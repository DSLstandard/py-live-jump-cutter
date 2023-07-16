Archive of a program made for personal use.

Cuts lecture videos / lengthy YouTube tutorial videos in real-time.

# Example use
```console
$ # `vq` is the program name, short for video quiet-er
$ # `mpv` is from https://mpv.io/
$ vq -t -28 -i https://youtu.be/qeByhTF8WEw | mpv --cache-secs=1 -
```

# Help print
```console
$ vq -h
usage: vq [-h] [-v {debug,info,error}] [-t TOLERANCE] [-m AFTER_LOUD_SAVE_DURATION] [-f OUTPUT_FORMAT]
          [-z FONT_SCALE] [-i]
          input [output]

positional arguments:
  input                 Set the source of the input (can either be a file path, or a YouTube url).
  output                Set the output (can either be a file path, or '-' for stdout). (default: -)

options:
  -h, --help            show this help message and exit
  -v {debug,info,error}, --log-level {debug,info,error}
                        Set the log level (default: 20)
  -t TOLERANCE, --tolerance TOLERANCE
                        Set the tolerance level (in dBFS). (default: -20.0)
  -m AFTER_LOUD_SAVE_DURATION, --after-loud-save-duration AFTER_LOUD_SAVE_DURATION
                        Do not skip a silent chunk if between it and the most recent loud chunk is less than this
                        amount of seconds (default: 0.3)
  -f OUTPUT_FORMAT, --output-format OUTPUT_FORMAT
                        Destination container format, defaults to 'matroska' if dest is - (stdout). (default: None)
  -z FONT_SCALE, --font-scale FONT_SCALE
                        Specify the scale of the font used in --draw-info (default: 0.4)
  -i, --draw-info       Draw info at the bottom of the video? (default: False)
```

# `av` does not compile
See https://github.com/guillaumekln/faster-whisper/issues/560.
