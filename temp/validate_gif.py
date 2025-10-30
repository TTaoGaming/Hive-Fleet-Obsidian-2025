from PIL import Image, ImageSequence
from pathlib import Path
import json, sys
p = Path(sys.argv[1])
info = {'path': str(p)}
try:
    with Image.open(p) as im:
        info['format'] = im.format
        info['size'] = im.size
        frames = 0
        durations = []
        for f in ImageSequence.Iterator(im):
            frames += 1
            durations.append(f.info.get('duration'))
        info['frames'] = frames
        info['duration_ms_unique'] = sorted(set([d for d in durations if d is not None]))
        im.seek(0)
        im.seek(frames-1)
        info['verify'] = 'ok'
except Exception as e:
    info['verify'] = f'error: {e}'
print(json.dumps(info))
