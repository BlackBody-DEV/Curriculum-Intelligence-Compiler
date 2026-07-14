# Portable Release Package Layout v1

A package root contains `manifest.json` and declared files under `artifacts/`. The frozen layout is:

```text
<package-root>/
  manifest.json
  artifacts/
    sources/
    curriculum/
    procedures/
    questions/
    generation_families/
    signals/
    performance/
    review/
    validation/
    assets/
```

All paths are relative, use forward slashes, stay inside the package root, and avoid absolute paths, parent traversal, adaptive-platform paths, and user-specific paths. Undeclared files are invalid.

## Integrity

Each artifact descriptor carries SHA-256 and byte size. Manifest serialization is deterministic JSON with sorted keys, compact separators, ASCII output, and trailing newline. The package-level manifest checksum excludes its own recursive checksum field.
