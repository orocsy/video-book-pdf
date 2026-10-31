# Compression choices

Video size and PDF size measure different redundancy. A recording stores motion, repeated still frames and often audio. A book PDF needs one still per distinct page. Select good source frames directly; a lossless H.264 intermediate may be larger than the original HEVC video and adds no source information.

A scanned page is a bitmap. Unlike a publisher PDF it has no original text/font/vector representation to reuse. RGB + ordinary Flate may compress photographic or video noise poorly. Reversible JPEG 2000 uses wavelet prediction/coding without discarding RGB samples. Irreversible JPEG 2000 quantizes wavelet coefficients; JPEG uses block transforms and may subsample color. Both reading modes are lossy even with no resize. JPX is a PDF 1.5 image filter; test the recipient's viewer. AVIF/WebP are not standard PDF image filters and require decode/re-encode or nonstandard wrappers.

Keep dimensions fixed in the first comparison. Changing PPI alone changes physical page dimensions, not embedded pixel count or readability information. White borders cost little in an efficient codec, so cropping them seldom explains a dramatic byte reduction. Crop only after proving that no page content, folios, footnotes or arrows are removed, and retain the coordinate transform.

Mixed raster content can encode text and photos differently, but mask/segmentation mistakes can erase tiny labels or alter glyphs. Use it only with separate checks; do not claim it was tested when only whole-page codecs were compared. Binarization and palette quantization change pixels. Lossy JBIG2 symbol substitution is inappropriate where changed digits could matter. No AI upscaler can prove the text of an unreadable video frame.

A private 2026-10-31 application experiment compared JPEG 82/75/68, JPEG 4:4:4, irreversible JPX rates 30/40/50, and reversible JPX on six varied pages. At native 1668×2388, JPX rate 40 had higher PSNR than JPEG 82 on that sample, and adaptive JPX produced a 95-page PDF of 30,247,973 bytes versus JPEG 82's 41,663,853. This is a measured example, not a benchmark or promise for other books; neither file is pixel-lossless. Private book pages are intentionally absent from this repository.

Primary documentation:
- [Pillow image formats](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html): JPEG quality/subsampling, JPEG 2000 reversible transform and rate settings.
- [FFmpeg filters](https://ffmpeg.org/ffmpeg-filters.html): select, showinfo and source presentation timestamps.
- [OCRmyPDF JBIG2 notes](https://github.com/ocrmypdf/OCRmyPDF/blob/main/docs/jbig2.md): lossless versus historical lossy symbol coding.
