def ocr_image(path: str) -> str:\n    try:\n        open(path, 'rb').close()\n        return ''\n    except Exception:\n        return ''\n
