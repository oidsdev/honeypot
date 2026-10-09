---
name: "image-optimize"
description: "Shrink images with ImageMagick into a new file and leave the original in place. Use before an upload or an attachment."
---

# Image optimization

Make a smaller copy of a JPEG, PNG, or WebP with ImageMagick. The original file stays where it is.

## When to use

An image is larger than the place it is going: a page, an attachment, or a thumbnail. Resize it, drop the metadata, and write a new file. Compare the two before you replace anything.

## Install

ImageMagick 7 installs the `magick` command. ImageMagick 6 installs `convert`. Use whichever one exists.

```sh
magick -version || convert -version
```

```sh
# Debian / Ubuntu
sudo apt-get install imagemagick

# macOS
brew install imagemagick
```

Pick the binary once and reuse it:

```sh
if command -v magick >/dev/null; then IM=magick; else IM=convert; fi
```

## Commands

Shrink a photo so the longest side is at most 1600 pixels, bake in the orientation, strip metadata, and write a JPEG. The `>` suffix means "only shrink". Quote it so the shell does not treat it as a redirect.

```sh
"$IM" input.jpg -auto-orient -resize '1600x1600>' -quality 82 -strip output.jpg
```

PNG, still a new file. `-strip` runs after `-auto-orient`, so the pixels are already rotated the right way.

```sh
"$IM" input.png -auto-orient -resize '1600x1600>' -strip output.png
```

WebP from the same source:

```sh
"$IM" input.png -auto-orient -resize '1600x1600>' -quality 80 -strip output.webp
```

Look at dimensions and byte sizes before you keep the result.

```sh
identify input.jpg output.jpg
ls -l input.jpg output.jpg
```

## Gotchas

- `mogrify` writes over the file you name. These examples use `magick` or `convert` so the original stays put.
- `-strip` removes profiles, comments, and EXIF, including GPS. Run `-auto-orient` first, or a phone photo can come out sideways.
- An unquoted `1600x1600>` is a shell redirect. Keep the quotes.
- Quality `82` is a reasonable JPEG. Lower numbers get smaller and softer. Look at the output before you go further down.
- A file that is already small can grow when you change format. Keep the original when `ls` shows the new file is larger.

---
Also on Honeypot — a free, open index of skills for AI agents: https://honeypot-e6c.pages.dev
[![Indexed on Honeypot](https://honeypot-e6c.pages.dev/badge.svg)](https://honeypot-e6c.pages.dev)
