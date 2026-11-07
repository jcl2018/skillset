"""PDF writer and drawing primitives for tab2pdf. Standard library only (Pillow optional)."""

from __future__ import annotations

import zlib

from pdfkit import CJK_FONT_CANDIDATES, _warn, string_width  # noqa: F401


def pdf_escape(s: str) -> bytes:
    out = bytearray()
    for ch in s:
        b = ch.encode("cp1252")
        if b in (b"(", b")", b"\\"):
            out += b"\\" + b
        elif b[0] < 32 or b[0] > 126:
            out += ("\\%03o" % b[0]).encode("ascii")
        else:
            out += b
    return bytes(out)


def is_base14_safe(s: str) -> bool:
    try:
        s.encode("cp1252")
        return True
    except UnicodeEncodeError:
        return False


class RasterCache:
    """Rasterize a text run that no base-14 font can express."""

    def __init__(self) -> None:
        self._font_path: str | None = None
        self._items: dict[tuple[str, str, int], tuple[int, int, bytes, float]] = {}
        self._checked = False

    def font_path(self) -> str | None:
        if not self._checked:
            self._checked = True
            import os
            for p in CJK_FONT_CANDIDATES:
                if os.path.exists(p):
                    self._font_path = p
                    break
        return self._font_path

    def available(self) -> bool:
        try:
            import PIL  # noqa: F401
        except Exception:
            return False
        return self.font_path() is not None

    def render(self, text: str, size: float, bold: bool):
        """Return (key, width_pt, height_pt) for a rasterized run."""
        from PIL import Image, ImageDraw, ImageFont

        scale = 4                      # supersample, then place at point size
        px = max(8, int(round(size * scale)))
        key = (text, "b" if bold else "r", px)
        if key in self._items:
            w, h, _data, wpt, bl = self._items[key]
            return key, wpt, h / scale, bl

        font = ImageFont.truetype(self.font_path(), px)
        probe = Image.new("L", (1, 1), 255)
        bbox = ImageDraw.Draw(probe).textbbox((0, 0), text, font=font)
        w = max(1, bbox[2] - bbox[0] + 2 * scale)
        h = max(1, bbox[3] - bbox[1] + 2 * scale)
        img = Image.new("L", (w, h), 255)
        ImageDraw.Draw(img).text((-bbox[0] + scale, -bbox[1] + scale), text,
                                 font=font, fill=0)
        # Distance from the TOP of this cropped image down to the font baseline.
        # Deriving it from the ink box instead makes the baseline jump whenever
        # the string happens to gain or lose a descender.
        ascent, _descent = font.getmetrics()
        baseline_px = ascent - bbox[1] + scale
        data = img.tobytes()
        self._items[key] = (w, h, data, w / scale, baseline_px / scale)
        return key, w / scale, h / scale, baseline_px / scale

    def items(self):
        return self._items


class PDF:
    def __init__(self, width: float, height: float) -> None:
        self.width = width
        self.height = height
        self.pages: list[list[bytes]] = []
        self.page_images: list[set] = []
        self._ops: list[bytes] = []
        self._imgs: set = set()
        self.raster = RasterCache()

    # -- page control -----------------------------------------------------
    def new_page(self) -> None:
        self.flush()
        self._ops = []
        self._imgs = set()

    def flush(self) -> None:
        if self._ops:
            self.pages.append(self._ops)
            self.page_images.append(self._imgs)

    # -- drawing ----------------------------------------------------------
    def text(self, x: float, y: float, s: str, font: str, size: float,
             gray: float = 0.0) -> None:
        """Draw `s` with its baseline at y."""
        if not s:
            return
        if font == "F1" and not is_base14_safe(s):
            # A tab row is a COLUMN GRID. Rasterizing it would swap fixed-pitch
            # Courier for a proportional bitmap and silently slide every fret
            # digit out from under its beat, so substitute and say so instead.
            bad = sorted({c for c in s if not is_base14_safe(c)})
            _warn("tab line contains %s, which no fixed-pitch PDF font can show - "
                  "replaced with '?' to keep the columns aligned: %s"
                  % (", ".join(repr(c) for c in bad), s.strip()[:60]))
            s = "".join(c if is_base14_safe(c) else "?" for c in s)
        if is_base14_safe(s):
            self._ops.append(
                b"BT /%s %.2f Tf %.3f g 1 0 0 1 %.2f %.2f Tm (%s) Tj ET\n"
                % (font.encode("ascii"), size, gray, x, y, pdf_escape(s))
            )
            return
        if not self.raster.available():
            _warn("lossy: non-Latin text needs Pillow and a CJK font; printed as '?': %s"
                  % s.strip()[:40])
            self.text(x, y, s.encode("ascii", "replace").decode("ascii"),
                      font, size, gray)
            return
        key, w, h, baseline = self.raster.render(s, size, bold=font.endswith("B"))
        self._imgs.add(key)
        name = self._img_name(key)
        # cm places the image by its BOTTOM edge, so drop it by whatever sits
        # below the baseline. Now the glyph baseline lands exactly on y.
        self._ops.append(
            b"q %.2f 0 0 %.2f %.2f %.2f cm /%s Do Q\n"
            % (w, h, x, y - (h - baseline), name.encode("ascii"))
        )

    def stem(self, x: float, y0: float, y1: float, w: float = 0.7) -> None:
        self._ops.append(b"0 G %.2f w %.2f %.2f m %.2f %.2f l S\n" % (w, x, y0, x, y1))

    def beam(self, x0: float, y: float, x1: float, h: float = 1.7) -> None:
        self._ops.append(b"0 g %.2f %.2f %.2f %.2f re f\n" % (x0, y, x1 - x0, h))

    def flag(self, x: float, y: float, g: float, down: bool = True) -> None:
        """Guitar Pro's eighth-note flag, as a filled outline, hanging from a stem
        that points down. Proportions measured on the reference frame against
        the stave gap `g`: it leaves the stem's end, swells out 0.55 g to the
        right a third of the way up, and tapers back to the stem 1.8 g up. `y`
        is the stem's END (its lowest point); the flag rises from there."""
        s = 1.0 if down else -1.0
        self._ops.append(
            b"0 g %.2f %.2f m %.2f %.2f %.2f %.2f %.2f %.2f c "
            b"%.2f %.2f %.2f %.2f %.2f %.2f c f\n"
            % (x, y,
               x + 0.05 * g, y + s * 0.30 * g, x + 0.60 * g, y + s * 0.55 * g, x + 0.50 * g, y + s * 1.25 * g,
               x + 0.42 * g, y + s * 0.75 * g, x + 0.12 * g, y + s * 0.60 * g, x, y + s * 0.40 * g))

    def quarter_rest(self, x: float, y: float, g: float) -> None:
        """Guitar Pro's quarter rest, drawn on the stave: the zigzag stroke, 2.25
        stave gaps tall, centred on the stave's middle line `y`."""
        h = 2.25 * g
        top, bot = y + h / 2.0, y - h / 2.0
        p = [(x - 0.10 * g, top), (x + 0.20 * g, top - 0.30 * h), (x - 0.05 * g, top - 0.52 * h),
             (x + 0.22 * g, bot + 0.20 * h), (x - 0.02 * g, bot + 0.26 * h), (x - 0.18 * g, bot + 0.08 * h),
             (x + 0.02 * g, bot), (x - 0.22 * g, bot + 0.22 * h), (x + 0.02 * g, bot + 0.40 * h),
             (x - 0.26 * g, top - 0.56 * h), (x + 0.02 * g, top - 0.32 * h)]
        ops = b"0 g %.2f %.2f m " % p[0] + b"".join(b"%.2f %.2f l " % q for q in p[1:]) + b"h f\n"
        self._ops.append(ops)

    def eighth_rest(self, x: float, y: float, g: float) -> None:
        """Guitar Pro's eighth rest: a dot on the stave's middle line `y` with a
        stroke falling to the lower right, 1.2 stave gaps tall."""
        self.notehead(x - 0.08 * g, y + 0.10 * g, 0.18 * g, 0.16 * g, True)
        self._ops.append(b"0 G %.2f w %.2f %.2f m %.2f %.2f l S\n"
                         % (0.08 * g, x + 0.14 * g, y + 0.12 * g, x - 0.08 * g, y - 0.70 * g))

    def notehead(self, cx: float, cy: float, rx: float, ry: float,
                 filled: bool = True) -> None:
        k = 0.5523
        self._ops.append(
            b"0 g 0 G 0.7 w %.2f %.2f m "
            b"%.2f %.2f %.2f %.2f %.2f %.2f c %.2f %.2f %.2f %.2f %.2f %.2f c "
            b"%.2f %.2f %.2f %.2f %.2f %.2f c %.2f %.2f %.2f %.2f %.2f %.2f c %s\n"
            % (cx - rx, cy,
               cx - rx, cy + ry * k, cx - rx * k, cy + ry, cx, cy + ry,
               cx + rx * k, cy + ry, cx + rx, cy + ry * k, cx + rx, cy,
               cx + rx, cy - ry * k, cx + rx * k, cy - ry, cx, cy - ry,
               cx - rx * k, cy - ry, cx - rx, cy - ry * k, cx - rx, cy,
               b"f" if filled else b"S"))

    def dot(self, cx: float, cy: float, r: float = 0.8) -> None:
        self.notehead(cx, cy, r, r, True)

    def repeat_bar(self, x: float, y0: float, y1: float, opening: bool) -> None:
        """A repeat barline: thick + thin + the two dots, facing the music.

        This is the sign for "play this SECTION again". The single-measure
        repeat sign says something different - repeat the ONE bar before it -
        so it is the wrong mark for a figure that spans several bars.
        """
        d = 1.0 if opening else -1.0
        self._ops.append(b"0 g %.2f %.2f %.2f %.2f re f\n"
                         % (x - (0.0 if opening else 1.9), y0, 1.9, y1 - y0))
        self._ops.append(b"0 G 0.7 w %.2f %.2f m %.2f %.2f l S\n"
                         % (x + d * 3.2, y0, x + d * 3.2, y1))
        mid = (y0 + y1) / 2.0
        for off in (-1.0, 1.0):
            self.dot(x + d * 5.6, mid + off * (y1 - y0) * 0.17, 0.9)

    def slide(self, x0: float, y0: float, x1: float, y1: float) -> None:
        """The stroke between the note you leave and the note you land on."""
        self._ops.append(b"0 G 0.9 w %.2f %.2f m %.2f %.2f l S\n"
                         % (x0, y0, x1, y1))

    def rule(self, x0: float, y: float, x1: float, gray: float = 0.75) -> None:
        self._ops.append(b"%.3f G %.2f w %.2f %.2f m %.2f %.2f l S\n"
                         % (gray, 0.5, x0, y, x1, y))

    @staticmethod
    def _img_name(key) -> str:
        # zlib.crc32, not hash(): PYTHONHASHSEED is salted per process, and a
        # renderer whose output bytes move between identical runs is one you
        # cannot diff.
        return "Im%08x" % (zlib.crc32(repr(key).encode("utf-8")) & 0xFFFFFFFF)

    # -- serialize --------------------------------------------------------
    def build(self, title: str, author: str) -> bytes:
        self.flush()
        objs: list[bytes] = []

        def add(body: bytes) -> int:
            objs.append(body)
            return len(objs)          # 1-based object number

        fonts = {
            "F1": b"/Courier",
            "F2": b"/Helvetica-Bold",
            "F3": b"/Helvetica",
            "F4": b"/Helvetica-Oblique",
        }
        font_ids = {}
        for name, base in fonts.items():
            font_ids[name] = add(
                b"<< /Type /Font /Subtype /Type1 /BaseFont %s "
                b"/Encoding /WinAnsiEncoding >>" % base
            )

        img_ids = {}
        for key, (w, h, data, _wpt, _bl) in self.raster.items().items():
            comp = zlib.compress(data, 9)
            img_ids[key] = add(
                b"<< /Type /XObject /Subtype /Image /Width %d /Height %d "
                b"/ColorSpace /DeviceGray /BitsPerComponent 8 "
                b"/Filter /FlateDecode /Length %d >>\nstream\n%s\nendstream"
                % (w, h, len(comp), comp)
            )

        pages_id = len(objs) + 2 * len(self.pages) + 1
        page_ids = []
        for ops, imgs in zip(self.pages, self.page_images):
            stream = zlib.compress(b"".join(ops), 9)
            cid = add(b"<< /Filter /FlateDecode /Length %d >>\nstream\n%s\nendstream"
                      % (len(stream), stream))
            xobjs = b""
            if imgs:
                xobjs = b"/XObject << " + b" ".join(
                    b"/%s %d 0 R" % (self._img_name(k).encode("ascii"), img_ids[k])
                    for k in sorted(imgs, key=self._img_name)
                ) + b" >> "
            res = b"/Font << " + b" ".join(
                b"/%s %d 0 R" % (n.encode("ascii"), font_ids[n]) for n in sorted(fonts)
            ) + b" >> " + xobjs
            page_ids.append(add(
                b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %.2f %.2f] "
                b"/Resources << %s>> /Contents %d 0 R >>"
                % (pages_id, self.width, self.height, res, cid)
            ))

        real_pages_id = add(
            b"<< /Type /Pages /Count %d /Kids [%s] >>"
            % (len(page_ids), b" ".join(b"%d 0 R" % p for p in page_ids))
        )
        assert real_pages_id == pages_id, "page-tree id prediction drifted"

        info_id = add(b"<< /Title (%s) /Author (%s) /Producer (bass-tab tab2pdf) >>"
                      % (pdf_escape(title[:120]) if is_base14_safe(title) else b"Bass tab",
                         pdf_escape(author[:120]) if is_base14_safe(author) else b""))
        cat_id = add(b"<< /Type /Catalog /Pages %d 0 R >>" % pages_id)

        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for i, body in enumerate(objs, start=1):
            offsets.append(len(out))
            out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
        xref = len(out)
        out += b"xref\n0 %d\n" % (len(objs) + 1)
        out += b"0000000000 65535 f \n"
        for off in offsets[1:]:
            out += b"%010d 00000 n \n" % off
        out += (b"trailer\n<< /Size %d /Root %d 0 R /Info %d 0 R >>\nstartxref\n%d\n%%%%EOF\n"
                % (len(objs) + 1, cat_id, info_id, xref))
        return bytes(out)

