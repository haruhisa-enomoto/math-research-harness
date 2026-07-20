from __future__ import annotations

import importlib.util
import json
import shutil
import sys


def main() -> None:
    checks = {
        "python": {"available": True, "version": sys.version.split()[0]},
        "python_modules": {
            "fitz": importlib.util.find_spec("fitz") is not None,
            "fontTools": importlib.util.find_spec("fontTools") is not None,
        },
        "commands": {
            command: shutil.which(command)
            for command in (
                "curl",
                "ocrmypdf",
                "tesseract",
                "djvused",
                "djvutxt",
                "ddjvu",
                "c44",
            )
        },
    }
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()
