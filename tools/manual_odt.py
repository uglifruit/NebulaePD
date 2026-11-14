#!/usr/bin/env python3
"""Build the updated instrument manual from the owner's ODT plus markdown sections.

  python tools/manual_odt.py                       # "Nebulae PD instruments.odt" -> docs/manual/Nebulae instruments.odt
  python tools/manual_odt.py --into-owner          # the same, written into the owner's own document (asked for
                                                   # 2026-11-14), with a dated backup copy in docs/manual/

The owner's document ("Nebulae PD instruments.odt", repo root, edited in LibreOffice) is kept as it is. The new
sections are written in a small markdown subset in docs/manual/*.md, and get the document's own look (its heading,
body, table and grey panel-map styles):
  00_*.md   go in front of everything (a page of their own); the rest are appended in name order
  # / ## / ###  headings (each # starts a new page),  - bullets,  1. numbered,  | tables | (first row = header),
  ``` blocks = the grey fixed-width panel maps,  **bold**,  `code` (fixed width),  blank line = new paragraph;
  a file whose first line is "@include ../OTHER.md" uses that doc instead (one source for both)
FIXES below corrects text in the owner's part (each must match exactly once, or already be fixed).

The generated parts are wrapped in bookmarks (NebulaePD-front-start/end, NebulaePD-back-start/end), so building
from a document that already holds them (--into-owner, again) first removes them and their NB* styles: the owner's
own text is never touched, and nothing is duplicated.
"""
import argparse
import os
import re
import sys
import zipfile
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "Nebulae PD instruments.odt")
OUT = os.path.join(ROOT, "docs", "manual", "Nebulae instruments.odt")
SECTIONS = os.path.join(ROOT, "docs", "manual")

FIXES = [  # (old, new) in content.xml; the resonator has had 4 voices since 2026-11-10
    (">A one-voice </text:span>", ">A four-voice </text:span>"),
]

# new automatic styles, modelled on the document's own (P1 = a heading 1, Table18 = a striped table)
STYLES = """{h1first}
<style:style style:name="NBH1" style:family="paragraph" style:parent-style-name="Heading_20_1"><style:paragraph-properties fo:margin-left="0cm" fo:margin-right="0cm" fo:margin-top="0cm" fo:margin-bottom="0.423cm" style:contextual-spacing="false" fo:line-height="125%" fo:orphans="2" fo:widows="2" fo:text-indent="0cm" style:auto-text-indent="false" fo:break-before="page" fo:padding-left="0cm" fo:padding-right="0cm" fo:padding-top="0cm" fo:padding-bottom="0.049cm" fo:border-left="none" fo:border-right="none" fo:border-top="none" fo:border-bottom="0.06pt solid #d1d9e0"/><style:text-properties fo:color="#1f2328" style:font-name="Arial1" fo:font-size="14pt" fo:font-weight="bold" style:font-size-asian="14pt" style:font-weight-asian="bold" style:font-size-complex="14pt" style:font-weight-complex="bold"/></style:style>
<text:list-style style:name="NBnum"><text:list-level-style-number text:level="1" style:num-suffix="." style:num-format="1"><style:list-level-properties text:list-level-position-and-space-mode="label-alignment"><style:list-level-label-alignment text:label-followed-by="listtab" text:list-tab-stop-position="0.9cm" fo:text-indent="-0.6cm" fo:margin-left="0.9cm"/></style:list-level-properties></text:list-level-style-number></text:list-style>
<text:list-style style:name="NBbul"><text:list-level-style-bullet text:level="1" text:bullet-char="•"><style:list-level-properties text:list-level-position-and-space-mode="label-alignment"><style:list-level-label-alignment text:label-followed-by="listtab" text:list-tab-stop-position="0.9cm" fo:text-indent="-0.5cm" fo:margin-left="0.9cm"/></style:list-level-properties></text:list-level-style-bullet></text:list-style>
<style:style style:name="NBpageend" style:family="paragraph" style:parent-style-name="Standard"><style:paragraph-properties fo:break-after="page"/></style:style>
<style:style style:name="NBlist" style:family="paragraph" style:parent-style-name="Standard"><style:paragraph-properties fo:margin-top="0cm" fo:margin-bottom="0.1cm" style:contextual-spacing="false"/><style:text-properties fo:color="#1f2328" style:font-name="Arial1" fo:font-size="10pt" style:font-size-asian="10pt" style:font-size-complex="10pt"/></style:style>
<style:style style:name="NBcell" style:family="paragraph" style:parent-style-name="Table_20_Contents"><style:paragraph-properties fo:margin-left="0cm" fo:margin-right="0cm" fo:margin-top="0cm" fo:margin-bottom="0cm" style:contextual-spacing="false" fo:text-indent="0cm" style:auto-text-indent="false"/><style:text-properties style:font-name="Arial1" fo:font-size="9pt" style:font-size-asian="9pt" style:font-size-complex="9pt"/></style:style>
<style:style style:name="NBcellhead" style:family="paragraph" style:parent-style-name="Table_20_Heading"><style:paragraph-properties fo:margin-left="0cm" fo:margin-right="0cm" fo:text-indent="0cm" style:auto-text-indent="false" fo:text-align="start"/><style:text-properties style:font-name="Arial1" fo:font-size="9pt" fo:font-weight="bold" style:font-size-asian="9pt" style:font-size-complex="9pt"/></style:style>
<style:style style:name="NBbold" style:family="text"><style:text-properties fo:font-weight="bold" style:font-weight-asian="bold" style:font-weight-complex="bold"/></style:style>
<style:style style:name="NBcode" style:family="text"><style:text-properties style:font-name="Liberation Mono" fo:font-family="'Liberation Mono'" style:font-family-generic="modern" style:font-pitch="fixed" fo:font-size="9pt"/></style:style>
"""
STYLES = STYLES.replace("{h1first}", re.search(r'<style:style style:name="NBH1".*?</style:style>', STYLES, re.S).group(0)
                        .replace('"NBH1"', '"NBH1first"').replace(' fo:break-before="page"', ''))
WIDTH = 19.001  # cm, as the document's tables


def table_styles(name, widths):
    s = ('<style:style style:name="%s" style:family="table"><style:table-properties style:width="%.3fcm" '
         'table:align="left"/></style:style>' % (name, WIDTH))
    for i, w in enumerate(widths):
        s += ('<style:style style:name="%s.%s" style:family="table-column"><style:table-column-properties '
              'style:column-width="%.3fcm"/></style:style>' % (name, chr(65 + i), w))
    return s


def inline(text):
    """**bold**, `code`, plain -> ODF spans."""
    out = []
    for part in re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", text):
        if not part:
            continue
        if part.startswith("**"):
            out.append('<text:span text:style-name="NBbold">%s</text:span>' % spaces(part[2:-2]))
        elif part.startswith("`"):
            out.append('<text:span text:style-name="NBcode">%s</text:span>' % spaces(part[1:-1]))
        else:
            out.append(spaces(part))
    return "".join(out)


def spaces(text):
    """Escape, and keep runs of spaces (ODF collapses them otherwise)."""
    text = escape(text)
    return re.sub(r"  +", lambda m: " " + '<text:s text:c="%d"/>' % (len(m.group(0)) - 1), text)


class Builder(object):
    def __init__(self):
        self.styles = []
        self.ntables = 0
        self.first_h1 = True

    def table(self, rows):
        cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
        cells = [r for r in cells if not all(re.match(r"^:?-+:?$", c) for c in r if c)]
        n = max(len(r) for r in cells)
        plain = [[re.sub(r"[*`]", "", r[i]) if i < len(r) else "" for i in range(n)] for r in cells]
        lens = [max(len(r[i]) for r in plain) for i in range(n)]
        # every column fits its longest word (9 pt Arial, ~0.19 cm a character, plus the cell padding);
        # what is left is shared by the amount of text
        need = [0.75 + 0.19 * max([len(w) for r in plain for w in r[i].split()] + [3]) for i in range(n)]
        spare = max(0.0, WIDTH - sum(need))
        weights = [min(max(l, 4), 80) for l in lens]
        widths = [need[i] + spare * weights[i] / sum(weights) for i in range(n)]
        widths = [w * WIDTH / sum(widths) for w in widths]
        self.ntables += 1
        name = "NBT%d" % self.ntables
        self.styles.append(table_styles(name, widths))
        x = ['<table:table table:name="%s" table:style-name="%s">' % (name, name)]
        x += ['<table:table-column table:style-name="%s.%s"/>' % (name, chr(65 + i)) for i in range(n)]
        for ri, r in enumerate(cells):
            r = r + [""] * (n - len(r))
            row = "Table18.1" if ri % 2 == 0 else "Table18.3"
            para = "NBcellhead" if ri == 0 else "NBcell"
            if ri == 0:
                x.append("<table:table-header-rows>")
            x.append('<table:table-row table:style-name="%s">' % row)
            for c in r:
                x.append('<table:table-cell table:style-name="Table18.A1" office:value-type="string">'
                         '<text:p text:style-name="%s">%s</text:p></table:table-cell>' % (para, inline(c)))
            x.append("</table:table-row>")
            if ri == 0:
                x.append("</table:table-header-rows>")
        x.append("</table:table>")
        return "".join(x)

    def convert(self, md):
        lines = md.replace("\r\n", "\n").split("\n")
        out, para, i = [], [], 0

        def flush():
            if para:
                out.append('<text:p text:style-name="P15">%s</text:p>' % inline(" ".join(para)))
                del para[:]
        while i < len(lines):
            line = lines[i]
            s = line.strip()
            if s.startswith("```"):
                flush()
                i += 1
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    out.append('<text:p text:style-name="P34">%s</text:p>' % spaces(lines[i].rstrip() or " "))
                    i += 1
                out.append('<text:p text:style-name="P39"/>')
            elif s.startswith("|"):
                flush()
                rows = []
                while i < len(lines) and lines[i].strip().startswith("|"):
                    rows.append(lines[i])
                    i += 1
                out.append(self.table(rows))
                out.append('<text:p text:style-name="P39"/>')
                continue
            elif re.match(r"^#{1,3} ", s):
                flush()
                level = len(s.split(" ")[0])
                style = {1: "NBH1first" if self.first_h1 else "NBH1", 2: "P6", 3: "P9"}[level]
                if level == 1:
                    self.first_h1 = False
                out.append('<text:h text:style-name="%s" text:outline-level="%d">%s</text:h>'
                           % (style, level, inline(s[level + 1:])))
            elif re.match(r"^(- |\d+\. )", s):
                flush()
                numbered = bool(re.match(r"^\d+\. ", s))
                items = []
                while i < len(lines) and re.match(r"^(- |\d+\. )", lines[i].strip()) and \
                        bool(re.match(r"^\d+\. ", lines[i].strip())) == numbered:
                    item = re.sub(r"^(- |\d+\. )", "", lines[i].strip())
                    i += 1
                    while i < len(lines) and lines[i].startswith("  ") and lines[i].strip() and \
                            not re.match(r"^(- |\d+\. )", lines[i].strip()):
                        item += " " + lines[i].strip()
                        i += 1
                    items.append(item)
                out.append('<text:list text:style-name="%s">' % ("NBnum" if numbered else "NBbul"))
                out += ['<text:list-item><text:p text:style-name="NBlist">%s</text:p></text:list-item>' % inline(t)
                        for t in items]
                out.append("</text:list>")
                continue
            elif not s:
                flush()
            else:
                para.append(s)
            i += 1
        flush()
        return "".join(out)


MARK = '<text:p text:style-name="Standard"><text:bookmark text:name="NebulaePD-%s"/></text:p>'


def strip_generated(content):
    """Remove earlier generated parts (between our bookmarks) and our NB* automatic styles."""
    for part in ("front", "back"):
        a = re.search(r'<text:p[^>]*>\s*<text:bookmark text:name="NebulaePD-%s-start"/>\s*</text:p>' % part, content)
        b = re.search(r'<text:p[^>]*>\s*<text:bookmark text:name="NebulaePD-%s-end"/>\s*</text:p>' % part, content)
        if a and b and b.end() > a.start():
            content = content[:a.start()] + content[b.end():]
    content = re.sub(r'<style:style style:name="NB[^"]*"[^>]*>.*?</style:style>\n?', "", content, flags=re.S)
    content = re.sub(r'<text:list-style style:name="NB[^"]*"[^>]*>.*?</text:list-style>\n?', "", content, flags=re.S)
    return content


def build(src, out, sections):
    files = sorted(f for f in os.listdir(sections) if f.endswith(".md"))
    front = [f for f in files if f.startswith("00_")]
    back = [f for f in files if not f.startswith("00_")]
    zin = zipfile.ZipFile(src)
    content = zin.read("content.xml").decode("utf8")
    content = strip_generated(content)
    for old, new in FIXES:
        if content.count(old) == 0 and content.count(new) >= 1:
            continue                                     # already fixed (the owner's document, rebuilt)
        if content.count(old) != 1:
            sys.exit("FIXES: %r found %d times" % (old, content.count(old)))
        content = content.replace(old, new)
    b = Builder()
    def read(f):
        text = open(os.path.join(sections, f), encoding="utf8").read()
        if text.startswith("@include "):              # the section is another doc, e.g. ../STORYTELLER.md
            text = open(os.path.join(sections, text.split(None, 1)[1].strip()), encoding="utf8").read()
        return text
    front_xml = "".join(b.convert(read(f)) for f in front)
    if front_xml:
        front_xml = MARK % "front-start" + front_xml + '<text:p text:style-name="NBpageend"/>' + MARK % "front-end"
    back_xml = MARK % "back-start" + "".join(b.convert(read(f)) for f in back) + MARK % "back-end"
    m = re.search(r"<office:text[^>]*>(\s*<text:sequence-decls>.*?</text:sequence-decls>)?", content, re.S)
    content = content[:m.end()] + front_xml + content[m.end():]
    end = content.rindex("</office:text>")
    content = content[:end] + back_xml + content[end:]
    a = content.index("</office:automatic-styles>")
    content = content[:a] + STYLES + "".join(b.styles) + content[a:]
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with zipfile.ZipFile(out, "w") as z:
        for info in zin.infolist():                      # mimetype first and stored, as ODF requires
            data = content.encode("utf8") if info.filename == "content.xml" else zin.read(info.filename)
            z.writestr(info, data, zipfile.ZIP_STORED if info.filename == "mimetype" else zipfile.ZIP_DEFLATED)
    return front, back


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=SRC)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--into-owner", action="store_true", help="write into the owner's document (backup first)")
    a = ap.parse_args()
    if a.into_owner:
        import shutil
        import time
        bak = os.path.join(SECTIONS, "Nebulae PD instruments (backup %s).odt" % time.strftime("%Y-%m-%d %H%M"))
        shutil.copy2(SRC, bak)
        tmp = SRC + ".new"
        front, back = build(SRC, tmp, SECTIONS)
        try:
            os.replace(tmp, SRC)
        except PermissionError:
            os.remove(tmp)
            os.remove(bak)
            sys.exit("The owner's document is open (LibreOffice holds it): close it there, then run this again. "
                     "Nothing was changed.")
        print("backup: %s" % bak)
        a.out = SRC
    else:
        front, back = build(a.src, a.out, SECTIONS)
    print("front: %s\nappended: %s\nwritten: %s" % (", ".join(front), ", ".join(back), a.out))


if __name__ == "__main__":
    main()
