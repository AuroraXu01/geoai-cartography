#!/usr/bin/env python3
"""Compose rendered map images into publication layouts."""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def font(size: int, bold: bool = False):
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Helvetica.ttf",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def load_image(path: Path) -> Image.Image:
    return Image.open(path.expanduser().resolve()).convert("RGB")


def fit_image(img: Image.Image, box: tuple[int, int], fill=(255, 255, 255)) -> Image.Image:
    canvas = Image.new("RGB", box, fill)
    copy = img.copy()
    copy.thumbnail(box, Image.LANCZOS)
    x = (box[0] - copy.width) // 2
    y = (box[1] - copy.height) // 2
    canvas.paste(copy, (x, y))
    return canvas


def draw_label(draw: ImageDraw.ImageDraw, xy: tuple[int, int], label: str):
    draw.text(xy, label, font=font(24, True), fill=(20, 20, 20))


def compose_grid(images, labels, cols, panel_size, gutter, margin, title=None):
    rows = math.ceil(len(images) / cols)
    title_h = 70 if title else 0
    width = margin * 2 + cols * panel_size[0] + (cols - 1) * gutter
    height = margin * 2 + title_h + rows * panel_size[1] + (rows - 1) * gutter
    out = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(out)
    if title:
        draw.text((margin, margin), title, font=font(34, True), fill=(20, 20, 20))
    y0 = margin + title_h
    for i, img in enumerate(images):
        row, col = divmod(i, cols)
        x = margin + col * (panel_size[0] + gutter)
        y = y0 + row * (panel_size[1] + gutter)
        out.paste(fit_image(img, panel_size), (x, y))
        if labels and i < len(labels):
            draw_label(draw, (x + 12, y + 10), labels[i])
    return out


def compose_main_sub(images, labels, panel_size, gutter, margin, title=None):
    if len(images) < 2:
        raise SystemExit("main-sub layout requires at least two images.")
    title_h = 70 if title else 0
    main_w, main_h = panel_size[0] * 2 + gutter, panel_size[1] * 2 + gutter
    sub_w, sub_h = panel_size
    sub_count = len(images) - 1
    sub_rows = max(2, sub_count)
    width = margin * 2 + main_w + gutter + sub_w
    height = margin * 2 + title_h + max(main_h, sub_rows * sub_h + (sub_rows - 1) * gutter)
    out = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(out)
    if title:
        draw.text((margin, margin), title, font=font(34, True), fill=(20, 20, 20))
    y0 = margin + title_h
    out.paste(fit_image(images[0], (main_w, main_h)), (margin, y0))
    if labels:
        draw_label(draw, (margin + 12, y0 + 10), labels[0])
    x_sub = margin + main_w + gutter
    for i, img in enumerate(images[1:], start=1):
        y = y0 + (i - 1) * (sub_h + gutter)
        out.paste(fit_image(img, (sub_w, sub_h)), (x_sub, y))
        if labels and i < len(labels):
            draw_label(draw, (x_sub + 12, y + 10), labels[i])
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Compose map image layouts.")
    parser.add_argument("--images", nargs="+", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--layout", choices=["grid", "side-by-side", "main-sub"], default="grid")
    parser.add_argument("--cols", type=int)
    parser.add_argument("--labels", nargs="*")
    parser.add_argument("--title")
    parser.add_argument("--panel-width", type=int, default=900)
    parser.add_argument("--panel-height", type=int, default=650)
    parser.add_argument("--gutter", type=int, default=28)
    parser.add_argument("--margin", type=int, default=48)
    args = parser.parse_args()

    images = [load_image(path) for path in args.images]
    labels = args.labels or []
    cols = args.cols or (len(images) if args.layout == "side-by-side" else 2)
    if args.layout in {"grid", "side-by-side"}:
        out = compose_grid(images, labels, cols, (args.panel_width, args.panel_height), args.gutter, args.margin, args.title)
    else:
        out = compose_main_sub(images, labels, (args.panel_width, args.panel_height), args.gutter, args.margin, args.title)
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    out.save(output, quality=95, subsampling=0)
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
