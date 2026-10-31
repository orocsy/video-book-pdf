# First-version evaluation (2026-10-31)

An independent agent received the Skill path and a normal task: create its own synthetic page-flip recording and produce ordered lossless/compact PDFs. It was not given expected fixes. It created four original numbered pages with diagrams, tiny footnotes, numbers, units and negation, rendered to a lossy 8.75-second 768×1024 H.264 clip.

The first proposal missed page 003: averaging change over white margins merged it with a similar-looking next page. The Skill's contact-sheet/folio review recovered it. The proposer was then changed to normalize difference over ink pixels and retain diagnostics for short excluded views. On the repeated independent run, all four complete pages were proposed automatically at 0.5, 2.5, 5.0 and 7.0 seconds. Two excluded views were independently confirmed as blended transitions. A new automated end-to-end synthetic regression accompanies the fix. This is a small forward test, not proof that arbitrary recordings need no review.

The independent check exported all four pages and compared each with a separate source-frame decode: RGB pixels matched. pypdf reopened both PDFs. Reversible JPX matched all source RGB pixels; compact passed recorded JPEG-baseline errors. CoreGraphics and Poppler rendered all four pages. Compact was 238,018 bytes versus lossless 659,474 bytes in that test. OCR showed punctuation/spacing differences and was not treated as a readability certificate. Reusing an existing output filename was refused and its hash stayed unchanged.

No real book material, credentials, API calls, installations or repository writes were delegated. Raw test artifacts remain local; only the method and aggregate measurements are published.
