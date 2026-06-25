"""Baut docs/Bedienungshandbuch.pdf aus docs/Bedienungshandbuch.md.

Reproduzierbar (kein /tmp). Bilder via ![alt](pfad). Deckblatt +
Inhaltsverzeichnis (mit Seitenzahlen) + PDF-Lesezeichen. Überschriften bleiben
bei ihrem Screenshot (CondPageBreak), Bilder moderat groß. Arial Unicode für
Umlaute/Symbole; Farb-Emoji werden für den Druck durch Klartext ersetzt.

Aufruf:  python3 tools/make_manual_pdf.py
"""
import os, re
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                HRFlowable, ListFlowable, ListItem, Image, KeepTogether,
                                PageBreak, CondPageBreak)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "docs/Bedienungshandbuch.md")
OUT = os.path.join(ROOT, "docs/Bedienungshandbuch.pdf")
BASE = os.path.dirname(SRC)

AUNI = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
pdfmetrics.registerFont(TTFont("AUni", AUNI))
pdfmetrics.registerFont(TTFont("AUni-Bold", BOLD if os.path.exists(BOLD) else AUNI))
pdfmetrics.registerFontFamily("AUni", normal="AUni", bold="AUni-Bold", italic="AUni", boldItalic="AUni-Bold")

EMOJI = {"⇧⌘":"Shift-Cmd-","⌘":"Cmd-","⇧":"Shift-",
         "🟢":"[grün]","🟡":"[gelb]","⚪":"[weiß]","💬":"(Kommentar)","⎇":"(Verzweigung)",
         "⚠":"(!)","✓":"OK","✔":"OK","🔍 ":"","🗑 ":"","🎁 ":"","✏ ":"","⛔ ":"",
         "🔍":"","🗑":"","🎁":"","✏":"","⛔":"","▶":">","►":">"}
def clean(s):
    for k,v in EMOJI.items(): s=s.replace(k,v)
    return s
def inline(s):
    s=clean(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
    s=re.sub(r"`([^`]+)`", r'<font face="Courier">\1</font>', s)
    s=re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s=re.sub(r"\*([^*]+)\*", r"<i>\1</i>", s)
    return s

C="#23241f"; GREEN="#3b5323"
body=ParagraphStyle("body",fontName="AUni",fontSize=10.5,leading=15,textColor=colors.HexColor(C))
h2=ParagraphStyle("h2",fontName="AUni-Bold",fontSize=15,leading=19,spaceBefore=16,spaceAfter=7,textColor=colors.HexColor(GREEN))
h3=ParagraphStyle("h3",fontName="AUni-Bold",fontSize=12,leading=16,spaceBefore=10,spaceAfter=4,textColor=colors.HexColor(C))
quote=ParagraphStyle("quote",parent=body,leftIndent=8,spaceBefore=8,spaceAfter=4,backColor=colors.HexColor("#f3f6ec"),
                     borderColor=colors.HexColor("#cdd9bf"),borderWidth=0.5,borderPadding=(7,7,7,9),textColor=colors.HexColor("#3a3d35"))
cap=ParagraphStyle("cap",parent=body,fontSize=8.5,leading=11,textColor=colors.HexColor("#888888"),alignment=1,spaceBefore=3)
cellS=ParagraphStyle("cell",parent=body,fontSize=9.5,leading=12)
cellH=ParagraphStyle("cellH",parent=cellS,fontName="AUni-Bold")

IMG_W=120*mm
def img_flowables(path,alt):
    full=os.path.join(BASE,path)
    iw,ih=ImageReader(full).getSize()
    w=IMG_W; h=w*ih/iw
    img=Image(full,width=w,height=h)
    fr=Table([[img]],colWidths=[w],hAlign="LEFT")
    fr.setStyle(TableStyle([("BOX",(0,0),(-1,-1),0.6,colors.HexColor("#c9c9c2")),
        ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
        ("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0)]))
    return [fr,Paragraph(inline(alt),cap),Spacer(1,10)], h

def make_table(rows):
    data=[[Paragraph(inline(c),cellH if r==0 else cellS) for c in row] for r,row in enumerate(rows)]
    tbl=Table(data,hAlign="LEFT")
    tbl.setStyle(TableStyle([("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#cccccc")),
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#eceae3")),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("LEFTPADDING",(0,0),(-1,-1),6),("RIGHTPADDING",(0,0),(-1,-1),6),
        ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4)]))
    return [Spacer(1,4),tbl,Spacer(1,8)]

class ManualDoc(SimpleDocTemplate):
    _bm = 0
    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph):
            st=flowable.style.name; txt=flowable.getPlainText()
            if st in ("h2","h3"):
                level = 0 if st=="h2" else 1
                self.notify("TOCEntry",(level,txt,self.page))
                self._bm += 1
                key = "bm%d" % self._bm
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(txt, key, level, 0)

lines=open(SRC,encoding="utf-8").read().split("\n")
story=[]
# --- Deckblatt ---
story+= [Spacer(1,55*mm),
    Paragraph("Opening Trainer", ParagraphStyle("t",fontName="AUni-Bold",fontSize=34,leading=40,alignment=1,textColor=colors.HexColor(C))),
    Spacer(1,6),
    Paragraph("Bedienungshandbuch", ParagraphStyle("s",fontName="AUni",fontSize=20,leading=26,alignment=1,textColor=colors.HexColor(GREEN))),
    Spacer(1,10), HRFlowable(width="55%",thickness=0.8,color=colors.HexColor("#cdd9bf")), Spacer(1,10),
    Paragraph("Persönlicher Schach-Eröffnungstrainer für macOS · Stand Juni 2026",
              ParagraphStyle("d",fontName="AUni",fontSize=11,leading=16,alignment=1,textColor=colors.HexColor("#777777"))),
    PageBreak()]
# --- Inhalt ---
toc=TableOfContents()
toc.levelStyles=[
    ParagraphStyle("toc0",fontName="AUni-Bold",fontSize=11,leading=18,textColor=colors.HexColor(C)),
    ParagraphStyle("toc1",fontName="AUni",fontSize=10,leading=15,leftIndent=14,textColor=colors.HexColor("#555555")),
]
story+= [Paragraph("Inhalt", ParagraphStyle("ih",fontName="AUni-Bold",fontSize=17,leading=22,spaceAfter=10,textColor=colors.HexColor(C))),
         toc, PageBreak()]

# --- Inhalt aus Markdown ---
def is_block(s):
    t=s.strip()
    return (t=="" or s.startswith("# ") or s.startswith("## ") or s.startswith("### ")
            or bool(re.match(r"^!\[", s)) or t.startswith("|") or t=="---"
            or s.startswith("> ") or bool(re.match(r"^\s*[-*] ", s)) or bool(re.match(r"^\s*\d+\. ", s)))
def image_height(path):
    iw,ih=ImageReader(os.path.join(BASE,path)).getSize()
    return IMG_W*ih/iw
def peek_image(j):
    # nächstes Bild — über Leerzeilen UND Zwischen-Überschriften hinweg; bricht ab,
    # sobald anderer Inhalt kommt (dann gehört kein Bild direkt zur Überschrift).
    while j<len(lines):
        s=lines[j].rstrip()
        if not s.strip() or s.startswith("## ") or s.startswith("### "): j+=1; continue
        m=re.match(r"^!\[(.*?)\]\((.+?)\)\s*$", s)
        return m.group(2) if m else None
    return None

i=0; skipped_title=False
while i<len(lines):
    ln=lines[i].rstrip()
    if not ln.strip(): i+=1; continue
    if ln.startswith("# "):
        if not skipped_title: skipped_title=True; i+=1; continue   # Titel steht auf dem Deckblatt
        ln="## "+ln[2:]
    if ln.startswith("## ") or ln.startswith("### "):
        # Überschriften-Lauf (z. B. »4.« + »4.1«) sammeln und mit dem folgenden
        # Bild als EINE Einheit halten -> keine verwaisten Titel, keine Riesenlücken.
        run=[]; k=i
        while k<len(lines):
            s=lines[k].rstrip()
            if not s.strip(): k+=1; continue
            if s.startswith("## "): run.append((h2,s[3:])); k+=1; continue
            if s.startswith("### "): run.append((h3,s[4:])); k+=1; continue
            break
        path=None
        if k<len(lines):
            mm_=re.match(r"^!\[(.*?)\]\((.+?)\)\s*$", lines[k].rstrip())
            if mm_: path=mm_.group(2)
        cond=len(run)*12*mm + ((image_height(path)+12*mm) if path else 20*mm)
        story.append(CondPageBreak(cond))
        for st,tx in run: story.append(Paragraph(inline(tx),st))
        i=k; continue
    m=re.match(r"^!\[(.*?)\]\((.+?)\)\s*$",ln)
    if m:
        flows,h=img_flowables(m.group(2),m.group(1)); story.append(CondPageBreak(h+6*mm)); story.extend(flows); i+=1; continue
    if ln.strip()=="---":
        story+=[Spacer(1,4),HRFlowable(width="100%",thickness=0.6,color=colors.HexColor("#dddddd")),Spacer(1,4)]; i+=1; continue
    if ln.lstrip().startswith("|"):
        rows=[]
        while i<len(lines) and lines[i].lstrip().startswith("|"):
            cells=[c.strip() for c in lines[i].strip().strip("|").split("|")]
            if not re.match(r"^[\s:\-]+$","".join(cells)): rows.append(cells)
            i+=1
        story.extend(make_table(rows)); continue
    if ln.startswith("> "):
        buf=[ln[2:]]; i+=1
        while i<len(lines) and lines[i].startswith("> "): buf.append(lines[i].rstrip()[2:]); i+=1
        story.append(Paragraph(inline(" ".join(buf)),quote)); continue
    if re.match(r"^\s*[-*] ",ln):
        items=[]
        while i<len(lines) and re.match(r"^\s*[-*] ",lines[i]):
            items.append(ListItem(Paragraph(inline(re.sub(r"^\s*[-*] ","",lines[i])),body),leftIndent=14)); i+=1
        story.append(ListFlowable(items,bulletType="bullet",start="•",leftIndent=12)); continue
    if re.match(r"^\s*\d+\. ",ln):
        items=[]
        while i<len(lines) and re.match(r"^\s*\d+\. ",lines[i]):
            items.append(ListItem(Paragraph(inline(re.sub(r"^\s*\d+\. ","",lines[i])),body),leftIndent=14)); i+=1
        story.append(ListFlowable(items,bulletType="1",leftIndent=14)); continue
    # Fließtext: weiche Zeilenumbrüche zu EINEM Absatz zusammenfassen
    buf=[ln]; i+=1
    while i<len(lines) and not is_block(lines[i]): buf.append(lines[i].rstrip()); i+=1
    story.append(Paragraph(inline(" ".join(buf)),body))

def footer(c,d):
    c.setFont("AUni",8); c.setFillColor(colors.HexColor("#999999"))
    c.drawCentredString(A4[0]/2,12*mm,f"Opening Trainer — Bedienungshandbuch · Seite {d.page}")

doc=ManualDoc(OUT,pagesize=A4,leftMargin=22*mm,rightMargin=22*mm,topMargin=18*mm,bottomMargin=20*mm,
              title="Opening Trainer — Bedienungshandbuch")
doc.multiBuild(story,onFirstPage=footer,onLaterPages=footer)
print("OK ->",OUT)
