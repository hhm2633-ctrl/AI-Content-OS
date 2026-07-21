import os
from pathlib import Path
from PIL import Image, ImageChops, ImageStat

base = Path(r'F:\AI-Content-OS-Data\source_intake\2026-07-19\deep_dive\screenshots')
out = []

for folder in sorted(base.glob('*/')):
    for masked in sorted(folder.glob('*_masked.png')):
        original = folder / masked.name.replace('_masked', '_original')
        if not original.exists():
            out.append((str(masked), 'no_original', 1.0, 0.0))
            continue
        try:
            a = Image.open(masked).convert('RGB')
            b = Image.open(original).convert('RGB')
            if a.size != b.size:
                b = b.resize(a.size)
            diff = ImageChops.difference(a, b)
            stat = ImageStat.Stat(diff)
            mean_total = (stat.mean[0] + stat.mean[1] + stat.mean[2]) / 3.0
            mean_ratio = mean_total / 255.0
            gray = diff.convert('L')
            hist = gray.histogram()
            nonzero = sum(hist[1:])
            nz_ratio = nonzero / (a.size[0] * a.size[1])

            # black pixel ratio on masked image (near-black)
            # threshold 12 for "black-ish" area
            g = Image.open(masked).convert('L')
            black_mask = g.point(lambda p: 1 if p <= 12 else 0, mode='1')
            black_ratio = sum(black_mask.getdata()) / (a.size[0] * a.size[1])

            status = 'unchanged' if nz_ratio < 0.002 and mean_ratio < 0.01 else 'changed'
            out.append((str(masked), status, nz_ratio, black_ratio))
        except Exception as e:
            out.append((str(masked), f'error:{e}', 1.0, 0.0))

for path, status, nz_ratio, black_ratio in out:
    print(f'{path}\t{status}\t{nz_ratio:.6f}\t{black_ratio:.6f}')
