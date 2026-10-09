---
name: "pdf-text"
description: "Extract selectable text from a PDF with pdftotext. Use when an agent needs the text layer of a PDF file."
---

# PDF text

Pull the text layer out of a PDF with Poppler's `pdftotext`. The result is plain text on stdout or in a file you name.

## When to use

The user hands you a PDF and wants the words in it: a page range, a whole document, or text that keeps the visual columns. This skill stops when the file has no text layer.

## Install

```sh
pdftotext -v
```

If that fails, install Poppler utils:

```sh
# Debian / Ubuntu
sudo apt-get install poppler-utils

# macOS
brew install poppler
```

`pdftotext -h` lists the flags for the build you have.

## Commands

Write the text to stdout. The second argument `-` means stdout. `-layout` keeps the columns where they were on the page. `-nopgbrk` leaves out the form-feed between pages.

```sh
pdftotext -layout -nopgbrk report.pdf -
```

Limit the range. Pages are numbered from 1.

```sh
pdftotext -f 1 -l 3 -layout report.pdf pages.txt
```

Check the output. A text layer comes back as words. An empty file means the pages are images.

```sh
wc -c pages.txt
```

## Gotchas

- `pdftotext` reads the embedded text layer. A scanned page with no text layer produces an empty result. Optical character recognition is a different tool.
- `-layout` is the right default for multi-column pages. `-raw` follows the content stream and is no longer the recommended mode.
- An encrypted file makes `pdftotext` exit with an error. Stop and ask the user. Do not guess passwords.
- Page numbers start at 1. `-f` and `-l` are inclusive.

---
Also on Honeypot — a free, open index of skills for AI agents: https://honeypot-e6c.pages.dev
[![Indexed on Honeypot](https://honeypot-e6c.pages.dev/badge.svg)](https://honeypot-e6c.pages.dev)
