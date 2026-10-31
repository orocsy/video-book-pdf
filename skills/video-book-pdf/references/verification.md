# What a check establishes

| Check | Establishes | Does not establish |
| --- | --- | --- |
| Source SHA-256 and exact PTS ticks | Same input and selected source instants | Complete book or correct page choice |
| Native PNG dimensions | No image downsampling after decode | Recovery of pre-video details |
| Folio/chapter/contact-sheet audit | Observed page-order gaps and duplicates | Unseen original pages exist in the recording |
| Reversible JPX decoded RGB equality, every page | Pixel-lossless relative to exported RGB | Original PDF/vector/font recovery |
| PSNR and edge error vs JPEG baseline | Measured distortion comparison | Correct digits, arrows or readable tiny type |
| OCR transcript comparison | Possible regression to investigate | Correct transcription or equal visual quality |
| CoreGraphics and Poppler renders | Compatibility on those engines/versions | All PDF readers or physical iPhone acceptance |

For a critical text comparison, normalize Unicode/whitespace, preserve digits, units, negatives and reading order, and show changed spans. Record the original and candidate image hashes and the OCR engine/version. Do not edit the OCR until a comparison looks better. A lower average OCR error can conceal one newly incorrect age, dose or negation.

Retain one source page per selected PTS. Do not use lossy reading copies as replacement OCR evidence. A later RAG pipeline should consume the original PNGs and separately store page, region, caption, order, source hashes and review status. A PDF is the reading artifact, not the knowledge database.
