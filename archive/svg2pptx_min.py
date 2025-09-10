#!/usr/bin/env python3
# svg2pptx_json.py
# - Reads minimalpptx.txt (base64→zip→JSON of parts)
# - Parses SVG with svgelements
# - Emits DrawingML <p:sp> shapes into slide1.xml
# - Updates slide size in presentation.xml
# - Writes a valid PPTX
import argparse, base64, io, json, zipfile, xml.etree.ElementTree as ET
from typing import Any, Dict, List, Union, Iterable, Tuple

# ---- deps: pip install svgelements ----
from svgelements import SVG, Shape, Path as SVGPath, Line, QuadraticBezier, CubicBezier, Arc, Color

# ===================== Utilities =====================
NS = {
    'p': "http://schemas.openxmlformats.org/presentationml/2006/main",
    'a': "http://schemas.openxmlformats.org/drawingml/2006/main",
    'r': "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    'pr':"http://schemas.openxmlformats.org/package/2006/relationships",
}
for k,v in NS.items(): ET.register_namespace(k, v)

EMU_PER_PX = 9525  # 96 dpi
def emu_px(x: float) -> int: return int(round(x * EMU_PER_PX))
def rgb_hex(c: Color|None):
    if not c or c.value is None: return None
    r,g,b = int(c.red*255), int(c.green*255), int(c.blue*255)
    return f"{r:02X}{g:02X}{b:02X}"
def stroke_cap(v): return {"butt":"flat","round":"rnd","square":"sq"}.get((v or "").lower(), "flat")
def stroke_join(v):
    v = (v or "").lower()
    return "rnd" if v=="round" else ("bevel" if v=="bevel" else "miter")

def flatten_segment(seg, samples=48):
    if isinstance(seg, Line):
        return [(seg.start, seg.end)]
    pts=[]; prev=seg.point(0.0)
    for i in range(1, samples+1):
        t = i/samples
        cur = seg.point(t)
        pts.append((prev, cur))
        prev = cur
    return pts

def to_lines(shape: Shape):
    # Any primitive -> Path -> sampled segments
    if isinstance(shape, SVGPath):
        segs=[]
        for seg in shape.segments():
            segs += flatten_segment(seg, 48 if isinstance(seg,(CubicBezier,QuadraticBezier,Arc)) else 1)
        return segs
    path = SVGPath(shape)
    segs=[]
    for seg in path.segments():
        segs += flatten_segment(seg, 48 if isinstance(seg,(CubicBezier,QuadraticBezier,Arc)) else 1)
    return segs

# ===================== JSON PPTX holder =====================
class PptxJSON:
    """
    JSON entries like:
      [{"path":"ppt/slides/slide1.xml","text":"<xml...>"},
       {"path":"ppt/theme/theme1.xml","text":"<xml...>"},
       {"path":"ppt/media/....","b64":"..."}]
    """
    def __init__(self, entries: List[Dict[str, Any]]):
        self.entries = entries
        self._index = {e["path"]: i for i,e in enumerate(entries)}

    @classmethod
    def from_minimalpptx_txt(cls, txt_path: str) -> "PptxJSON":
        raw = open(txt_path, "r", encoding="utf-8", errors="ignore").read()
        b64 = "".join(c for c in raw if c.isalnum() or c in "+/=\n\r")
        zbytes = base64.b64decode(b64)
        with zipfile.ZipFile(io.BytesIO(zbytes), "r") as zf:
            # pick first entry (usually fileObj.txt / fileObj.json)
            name = zf.namelist()[0]
            data = zf.read(name).decode("utf-8")
        obj = json.loads(data)
        if isinstance(obj, dict) and "files" in obj:
            obj = obj["files"]
        if not isinstance(obj, list):
            raise ValueError("Expected a list of JSON entries")
        return cls(obj)

    def get_text(self, path: str) -> str:
        i = self._index[path]
        e = self.entries[i]
        if "text" in e: return e["text"]
        if "b64" in e: return base64.b64decode(e["b64"]).decode("utf-8")
        if "data" in e: return base64.b64decode(e["data"]).decode("utf-8")
        if "content" in e:
            enc = (e.get("encoding") or "utf8").lower()
            b = base64.b64decode(e["content"]) if enc.startswith("base64") else str(e["content"]).encode("utf-8")
            return b.decode("utf-8")
        raise ValueError(f"{path}: no textual payload")

    def upsert_text(self, path: str, text: str):
        e = {"path": path, "text": text}
        if path in self._index:
            self.entries[self._index[path]] = e
        else:
            self._index[path] = len(self.entries)
            self.entries.append(e)

    def to_pptx_bytes(self) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for e in self.entries:
                path = e["path"]
                if "text" in e:
                    payload = e["text"].encode("utf-8")
                elif "b64" in e:
                    payload = base64.b64decode(e["b64"])
                elif "data" in e:
                    payload = base64.b64decode(e["data"])
                elif "content" in e:
                    enc = (e.get("encoding") or "utf8").lower()
                    payload = base64.b64decode(e["content"]) if enc.startswith("base64") else str(e["content"]).encode("utf-8")
                else:
                    raise ValueError(f"Entry missing payload: {path}")
                z.writestr(path, payload)
        return buf.getvalue()

# ===================== DrawingML emitters =====================
def make_sp_from_lines(lines, stroke_hex, stroke_w_px, cap, join, fill_hex, offx, offy, shape_id):
    p,a = NS['p'], NS['a']
    sp = ET.Element(f"{{{p}}}sp")
    nv = ET.SubElement(sp, f"{{{p}}}nvSpPr")
    ET.SubElement(nv, f"{{{p}}}cNvPr", id=str(shape_id), name=f"shape{shape_id}")
    ET.SubElement(nv, f"{{{p}}}cNvSpPr")
    spPr = ET.SubElement(sp, f"{{{p}}}spPr")

    xs=[pt.real for seg in lines for pt in seg]; ys=[pt.imag for seg in lines for pt in seg]
    minx,maxx = (min(xs), max(xs)) if xs else (0,0)
    miny,maxy = (min(ys), max(ys)) if ys else (0,0)

    xfrm = ET.SubElement(spPr, f"{{{a}}}xfrm")
    ET.SubElement(xfrm, f"{{{a}}}off", x=str(emu_px(minx-offx)), y=str(emu_px(miny-offy)))
    ET.SubElement(xfrm, f"{{{a}}}ext", cx=str(emu_px(maxx-minx)), cy=str(emu_px(maxy-miny)))

    cust = ET.SubElement(spPr, f"{{{a}}}custGeom")
    ET.SubElement(cust, f"{{{a}}}avLst"); ET.SubElement(cust, f"{{{a}}}gdLst")
    pl = ET.SubElement(cust, f"{{{a}}}pathLst")
    apath = ET.SubElement(pl, f"{{{a}}}path", w="0", h="0")

    cur=None
    for p0,p1 in lines:
        if cur is None or abs(p0-cur) > 1e-6:
            m = ET.SubElement(apath, f"{{{a}}}moveTo")
            ET.SubElement(m, f"{{{a}}}pt", x=str(emu_px(p0.real-offx)), y=str(emu_px(p0.imag-offy)))
        l = ET.SubElement(apath, f"{{{a}}}lnTo")
        ET.SubElement(l, f"{{{a}}}pt", x=str(emu_px(p1.real-offx)), y=str(emu_px(p1.imag-offy)))
        cur = p1
    if lines and abs(lines[0][0] - lines[-1][1]) < 1e-6:
        ET.SubElement(apath, f"{{{a}}}close")

    # stroke
    if stroke_hex and stroke_w_px and stroke_w_px > 0:
        ln = ET.SubElement(spPr, f"{{{a}}}ln", w=str(int(round(stroke_w_px * EMU_PER_PX))))
        ln.set("cap", stroke_cap(cap)); ln.set("cmpd","sng")
        sfill = ET.SubElement(ln, f"{{{a}}}solidFill"); ET.SubElement(sfill, f"{{{a}}}srgbClr", val=stroke_hex)
        j = stroke_join(join)
        if j == "bevel": ET.SubElement(ln, f"{{{a}}}bevel")
        elif j == "rnd": ET.SubElement(ln, f"{{{a}}}round")
        else: ln.set("miterLimit","400000")
    else:
        ET.SubElement(spPr, f"{{{a}}}ln", w="0")

    # fill
    if fill_hex:
        fill = ET.SubElement(spPr, f"{{{a}}}solidFill"); ET.SubElement(fill, f"{{{a}}}srgbClr", val=fill_hex)

    # empty tx body (required)
    tx = ET.SubElement(sp, f"{{{p}}}txBody")
    ET.SubElement(tx, f"{{{a}}}bodyPr"); ET.SubElement(tx, f"{{{a}}}lstStyle"); ET.SubElement(tx, f"{{{a}}}p")
    return sp

def slide_xml_from_shapes(shapes_xml: List[ET.Element]) -> str:
    p,a = NS['p'], NS['a']
    sld = ET.Element(f"{{{p}}}sld")
    c = ET.SubElement(sld, f"{{{p}}}cSld")
    tree = ET.SubElement(c, f"{{{p}}}spTree")
    nv = ET.SubElement(tree, f"{{{p}}}nvGrpSpPr")
    ET.SubElement(nv, f"{{{p}}}cNvPr", id="1", name=""); ET.SubElement(nv, f"{{{p}}}cNvGrpSpPr")
    ET.SubElement(tree, f"{{{p}}}grpSpPr")
    for s in shapes_xml: tree.append(s)
    clr = ET.SubElement(sld, f"{{{p}}}clrMapOvr"); ET.SubElement(clr, f"{{{a}}}masterClrMapping")
    return ET.tostring(sld, encoding="UTF-8", xml_declaration=True).decode("utf-8")

def update_presentation_size(presentation_xml: str, cx_emus: int, cy_emus: int) -> str:
    # parse and replace <p:sldSz cx=".." cy="..">
    root = ET.fromstring(presentation_xml)
    sldSz = root.find(f".//{{{NS['p']}}}sldSz")
    if sldSz is not None:
        sldSz.set("cx", str(cx_emus)); sldSz.set("cy", str(cy_emus))
    return ET.tostring(root, encoding="UTF-8", xml_declaration=True).decode("utf-8")

# ===================== Main conversion =====================
def convert(svg_path: str, minimal_txt: str, out_pptx: str):
    pj = PptxJSON.from_minimalpptx_txt(minimal_txt)

    svg = SVG.parse(svg_path)
    if svg.viewbox is not None:
        x0,y0,w,h = svg.viewbox.x, svg.viewbox.y, svg.viewbox.width, svg.viewbox.height
    else:
        x0,y0 = 0,0
        w = float(svg.width) if svg.width is not None else 800.0
        h = float(svg.height) if svg.height is not None else 600.0

    shapes=[]; sid=2
    for e in svg.elements():
        if not isinstance(e, Shape): continue
        if e.values.get('display','') == 'none': continue
        lines = to_lines(e)
        if not lines: continue
        stroke = rgb_hex(getattr(e,'stroke',None))
        fill   = rgb_hex(getattr(e,'fill',None))
        sw     = float(getattr(e,'stroke_width',0.0) or 0.0)
        cap    = getattr(e,'stroke_linecap',None)
        join   = getattr(e,'stroke_linejoin',None)
        shapes.append(make_sp_from_lines(lines, stroke, sw, cap, join, fill, x0, y0, sid))
        sid += 1

    # 1) Replace slide1.xml
    slide_xml = slide_xml_from_shapes(shapes)
    pj.upsert_text("ppt/slides/slide1.xml", slide_xml)

    # 2) Update presentation.xml size to match SVG canvas
    pres_xml = pj.get_text("ppt/presentation.xml")
    pres_xml = update_presentation_size(pres_xml, emu_px(w), emu_px(h))
    pj.upsert_text("ppt/presentation.xml", pres_xml)

    with open(out_pptx, "wb") as f:
        f.write(pj.to_pptx_bytes())

# ===================== CLI =====================
if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="SVG → PPTX (DrawingML) using minimalpptx.txt JSON package.")
    ap.add_argument("svg", help="input SVG")
    ap.add_argument("minimalpptx_txt", help="base64 ZIP → JSON (minimal PPTX) file")
    ap.add_argument("out_pptx", help="output PPTX path")
    args = ap.parse_args()
    convert(args.svg, args.minimalpptx_txt, args.out_pptx)
    print(f"OK → {args.out_pptx}")

