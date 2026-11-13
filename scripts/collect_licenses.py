"""Collect installed distribution metadata and license texts for release review."""
from importlib.metadata import distributions
from pathlib import Path
import shutil

destination = Path("dist/ChatScout/third-party-licenses")
for distribution in distributions():
    name = distribution.metadata.get("Name", "unknown")
    folder = destination / name
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "METADATA.txt").write_text(distribution.read_text("METADATA") or "", encoding="utf-8")
    for file in distribution.files or ():
        if any(word in file.name.casefold() for word in ("license", "licence", "copying", "copyright")):
            source = distribution.locate_file(file)
            if source.is_file():
                shutil.copy2(source, folder / file.name)
