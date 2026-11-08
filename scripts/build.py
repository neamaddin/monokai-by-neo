#!/usr/bin/env python3
"""Validate and reproducibly package the resource-only IntelliJ plugin."""
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]


def build():
    descriptor_path = ROOT / "META-INF/plugin.xml"
    descriptor = ET.parse(descriptor_path).getroot()
    if descriptor.tag != "idea-plugin":
        raise ValueError("Expected an idea-plugin descriptor")
    for field in ("id", "name", "version", "vendor", "idea-version", "depends"):
        if descriptor.find(field) is None:
            raise ValueError(f"Missing plugin field: {field}")
    extension = descriptor.find("extensions/bundledColorScheme")
    if extension is None:
        raise ValueError("Missing bundledColorScheme extension")
    relative_path = extension.attrib["path"].lstrip("/") + ".xml"
    scheme_path = ROOT / relative_path
    if not scheme_path.resolve().is_relative_to(ROOT):
        raise ValueError("Scheme path must stay inside the project")
    scheme = ET.parse(scheme_path).getroot()
    if scheme.tag != "scheme" or not scheme.get("name"):
        raise ValueError("Expected a named color scheme")
    if scheme.get("parent_scheme") != "Darcula":
        raise ValueError("The dark scheme must inherit from bundled Darcula")
    for section in ("colors", "attributes"):
        options = scheme.findall(f"{section}/option")
        if not options:
            raise ValueError(f"Missing scheme section: {section}")
        names = [option.attrib["name"] for option in options]
        if len(names) != len(set(names)):
            raise ValueError(f"Duplicate keys in {section}")
    resources = {
        "META-INF/plugin.xml": descriptor_path.read_bytes(),
        relative_path: scheme_path.read_bytes(),
    }
    output = ROOT / "Monokai_by_Neo.jar"
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for name, data in resources.items():
            info = ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    with ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise ValueError("Corrupt plugin archive")
        for name, data in resources.items():
            if archive.read(name) != data:
                raise ValueError(f"Packaged resource differs: {name}")
    print(f"Built {output.name}, version {descriptor.findtext('version')}")


if __name__ == "__main__":
    build()
