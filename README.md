# ASCII video

Default preview: https://maxlang7.github.io/ascii-video/

[Download the Ultra MP4](https://github.com/maxlang7/ascii-video/releases/download/v1.0.0/ultra-ascii.mp4) · [All videos and examples](https://github.com/maxlang7/ascii-video/releases/tag/v1.0.0)

A local MP4/MOV converter. It produces colored ASCII on black, a standalone HTML player, and a compressed H.264 MP4. Originals are preserved. No cloud service or API key.

## Open the converter

```sh
cd ~/Documents/ascii-video
nix-shell --run 'python serve.py'
```

Open http://localhost:8765, choose your video, select a preset, and click Convert. Outputs are in `outputs/<job>/`. Uploaded copies are retained in `uploads/`. Stop the server with Ctrl+C. It listens only on your computer.

## Command line

```sh
nix-shell --run 'python ascii_video.py /path/to/video.mov -o /path/to/new-output --preset tiny'
```

Use a new output directory each time. Default preset is `ultra`. Add `--audio` to keep mono 24 kbps AAC audio, or `--seconds 15` for a short sample.

| Preset | Columns | FPS | Color | MP4 CRF |
| --- | ---: | ---: | --- | ---: |
| tiny | 48 | 6 | No | 43 |
| small | 128 | 12 | 16 colors | 34 |
| detail | 256 | 20 | 16 colors | 38 |
| ultra | 320 | 24 | 16 colors | 36 |

The smallest preset sacrifices detail and smoothness. Size depends on the source motion and duration; a smaller MP4 is not guaranteed for every already compressed input. Audio is off by default. Audio adds about 180 KB per minute plus container overhead.

## How it works

FFmpeg samples the video into a dense character grid. Brightness chooses a glyph from ` .,:;i+*ox%#@`. Ink colors are normalized so dark parts of the image are not dimmed twice. Sharpening preserves small edges. The MP4 uses an exact glyph atlas, rendered with NumPy and Pillow.

The web player stores a very small H.264 video at character-grid resolution. A WebGL shader converts those decoded pixels to colored glyphs during playback, using an embedded glyph atlas. Canvas rendering is available when WebGL is unavailable. The webpage embeds both the proxy video and the atlas, so it remains a single portable file. You can inspect the characters by zooming in. The embedded video has only one pixel per character cell.

This is much smaller than storing every character grid independently, especially at 256 or 320 columns. The exported MP4 has its ASCII permanently rendered and will usually be larger than the HTML. Both are silent unless audio is requested. H.264 uses faststart for web playback.

## View or share

Double-click an output `index.html` in a current browser. WebGL gives smooth high-density rendering. The single HTML contains everything needed for playback, including optional audio. The MP4 download link requires `ascii.mp4` beside it. Upload the HTML alone, or the output directory, to any static host. This tool does not publish anything automatically.

Phone rotation is handled. High-density rendered MP4s require more conversion time and storage than tiny presets. Originals are preserved. In-progress conversions leave their output directory in place if interrupted.

## Test source

Full 347-second video: https://www.youtube.com/watch?v=rGbbhEi9a2A

The Instagram reel was inspiration only; it was not downloaded or converted. The default full-resolution conversion is in `test-ultra/`, using a 1710 × 1080 source. See `test-ultra/report.json` for measured sizes. Earlier outputs in `test-small/` and `test-tiny/` are retained for comparison.

## Validation of the revised renderer

The full detail export retains 346.6 seconds at 1536 × 980 and 20 fps. FFmpeg decoded the complete MP4 without errors. Browser checks covered WebGL rendering, playback, seeking, looping, direct file playback of the Ultra sample, and a MOV upload with embedded audio. The default character grid is 256 × 98 for the test source, compared with the earlier 80 × 26.

Measured full-video output: standalone HTML 1,604,749 bytes; embedded spatial proxy 1,186,571 bytes; rendered MP4 50,289,958 bytes. HD input was 155,612,295 bytes.

## Ultra default

Ultra is the default for the command line, local upload form, and web preview. The full test uses a 320 × 122 character grid, renders at 1920 × 1220 and 24 fps, and retains the full 346.58-second video. The standalone HTML is 2,183,810 bytes. The rendered H.264 MP4 is 113,669,949 bytes; it is distributed in Releases rather than Git history. The HD source is 155,612,295 bytes. The web player gives the best size-to-detail tradeoff.

GitHub Pages hosts the preview players. Run the Python converter locally to process your own files. The repository includes code and all finished preview pages; Releases includes MP4 downloads and an archive of the example outputs and test inputs.
