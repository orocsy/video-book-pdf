---
name: video-book-pdf
description: Recover ordered book or slide pages from a screen-recording video, export exact source frames, and build verified lossless or compact PDFs offline. Use for video-to-PDF, ebook page-flip recordings, oversized image PDFs, native-resolution preservation, page-gap audits, and compression/readability comparisons.
---

# Video book PDF

Produce a usable PDF plus evidence of page order, image fidelity and size. Preserve the source. Never claim that decoding a lossy video recovers the publisher's original PDF.

## Establish the target

Inspect the real video's duration, rotation, frame rate, resolution and hash with ffprobe. Verify that the clip contains complete pages. Confirm whether the user wants pixel equality to decoded RGB frames, a smaller reading copy, or both. A file-size target never licenses missing pages or an unsupported “lossless” claim.

Use a private working directory outside any public repository. Publish generic code and synthetic tests only. Read [verification.md](references/verification.md) before quality claims and [compression.md](references/compression.md) when choosing a codec.

## Recover pages

Run the bundled scripts with Python 3.12+, Pillow, NumPy, ffmpeg and ffprobe. JPEG 2000 requires Pillow built with OpenJPEG. Pin and record actual versions. The repository requirements include pypdf for independent PDF checks.

```bash
python scripts/recover_pages.py sample /absolute/video.mp4 /absolute/new-work
python scripts/recover_pages.py propose /absolute/new-work /absolute/new-work/proposals.json
```

These paths are relative to this skill directory. Sampling writes small PNG previews and exact source PTS ticks; it never transcodes an intermediate video. The proposer compares small frames for page changes and measures sharpness at a larger width. It normalizes change over ink regions so white margins do not hide small text changes. Its thresholds are recording-specific; short excluded views are recorded in a diagnostics JSON for review.

Review proposals against all sampled frames. Prefer a stable, sharp, complete page, not a turning-page edge. Generate contact sheets with Pillow if useful. Audit printed folios and chapter/cover pages. Inspect every discontinuity, near-duplicate, source timestamp gap and the final page. Include a missed page using its `samples.json` row; renumber `sequence` while preserving candidate identity and source timestamps. Increase sampling around quick flips when necessary. Never declare the book complete from a frame count alone. A white-margin heuristic can omit genuine pages.

Write the reviewed page map as a JSON array with unique positive `candidate`, contiguous `sequence` from 1, strictly increasing `video_pts`, and exact integer `pts_ticks` copied from samples. Keep unreviewed material explicitly proposed.

```bash
python scripts/recover_pages.py export /absolute/video.mp4 /absolute/new-work /absolute/new-work/reviewed.json /absolute/new-pages
```

Export performs one source decode and selects exact PTS ticks. Avoid rounded `-ss` seeks for proof-quality VFR extraction. It retains native resolution and writes PNG without changing pixels after video decoding. Existing destinations are refused, never cleared. An interrupted directory remains available for inspection; choose a new destination for retries.

## Compare PDF encodings

```bash
python scripts/pack_pdf.py --page-map /absolute/reviewed.json --pages-dir /absolute/new-pages --output /absolute/lossless.pdf --mode lossless --report /absolute/lossless-proof.json
python scripts/pack_pdf.py --page-map /absolute/reviewed.json --pages-dir /absolute/new-pages --output /absolute/reading.pdf --mode compact --rate 40 --report /absolute/reading-proof.json
```

- `lossless` uses reversible JPEG 2000 and requires decoded RGB equality for every page. Equality is to each exported RGB frame; source YUV and original book file are different objects.
- `compact` uses lossy JPEG 2000 without resizing or cropping. It increases bitrate per page until global pixel error and thin-stroke edge error are no worse than a native-size JPEG quality 82 baseline. Those metrics do not establish readable or correct text.
- `--mode jpeg` creates a widely supported baseline reading copy.
- `--quality-policy review --rate 50` tries a tighter size target without enforcing baseline errors. Treat its output as a candidate requiring extra inspection, never an automatically approved reading copy. Reports retain `readability_verified: false`.

Native dimensions, page order, per-page source hash, codec, actual rate, pixel/edge errors, output hash and byte count are recorded. Outputs are atomically published without clobbering existing files.

## Verify and deliver

Open with pypdf and render with at least two independent engines, such as CoreGraphics/PDFKit and Poppler. Check page count, aspect ratio, page order and every image stream. Reopen lossless streams and compare every pixel. On reading copies inspect native-size tiny text, colored text, numbers, units, negation, footnotes, arrows, diagrams and photographs. Compare OCR on a varied sample as a regression detector; inspect changed critical characters against the source. OCR agreement is not ground truth.

Deliver the PDF, page map and concise comparison table. Explain video-frame redundancy removal separately from image compression. Report exact MB (1,000,000 bytes), pages, fidelity mode, actual quality checks, gaps and unverified conditions. Keep lossless evidence available. Do not call JPEG/irreversible JPX or visually similar output “无损”. No generative restoration, character substitution, lossy JBIG2, arbitrary web upload or paid API is needed.
