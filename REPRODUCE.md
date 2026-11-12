# Reproduction and verification

The corpus input digest is `310e0d087477fb58cf4424229c62e930107afd6a4807567f5680df66a4fd5dde`. Each version records its source URL and source-byte SHA-256 in data/versions.json. The per-file dates, hashes and writing commits are listed in data/provisions.tsv.

Law text uses native official PDF text with whitespace normalization only. Two source parses produced identical bytes, and the resulting words equal fresh extraction from the unchanged source. Source comparisons establish equality to native extracted text; they do not certify every aspect of visual layout. No model corrected OCR or legal wording.

The shared date-reader check compares corpus input with git versions on each effective date and the preceding day. Source checks and storage checks are separate proofs. All 462 versions passed with zero text mismatches, trailer errors, missing date trailers, merges, backward committer timestamps or future commit dates.

The checked law-history tip is `707698ae171066cf69073ebbf45006dabab8168e`. The independent review reproduced that tip exactly from all 25 input batches, excluding closing documentation. The shared tool bundle is the coherent approved world-law-ops main revision `590053183eb05e4288e221c23feb9e5d8d600e6c`. Its reader, builder, checker, schema, documentation template and supporting modules are included unchanged apart from LF normalization and removal of marked private passages. The documentation was generated with that revision’s builder; the 462 law commits remain unchanged.

GPT-6 wrote extraction and build code, selected metadata and checked sources. It supplied no legal wording, amendment-credit guesses or corrected OCR.
