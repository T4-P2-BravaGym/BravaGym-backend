JPEG = b"\xff\xd8\xff\xe0" + bytes(16)
PNG = b"\x89PNG\r\n\x1a\n" + bytes(16)
WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 " + bytes(16)
SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
PDF = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"
EXE = b"MZ\x90\x00\x03\x00\x00\x00"
