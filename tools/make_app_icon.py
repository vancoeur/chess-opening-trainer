import os, pathlib, collections
os.environ["QT_QPA_PLATFORM"]="offscreen"
from PySide6 import QtSvg, QtGui, QtCore
from PySide6.QtGui import QImage, QPainter, QColor, QPainterPath, QFont, QTransform, QPolygonF, QPen
from PySide6.QtCore import QPointF
app=QtGui.QGuiApplication.instance() or QtGui.QGuiApplication([])
W=H=1024
def bgimg():
    RR='<rect x="0" y="0" width="1024" height="1024" rx="230" ry="230"'
    sq="".join(f'<rect x="{c*128}" y="{r*128}" width="128" height="128" fill="#2f78b8" opacity="0.15"/>' for r in range(8) for c in range(8) if (r+c)%2)
    defs='<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#7cb6e2"/><stop offset="1" stop-color="#4a90cf"/></linearGradient></defs>'
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}">{defs}<clipPath id="c">{RR}/></clipPath><g clip-path="url(#c)">{RR} fill="url(#g)"/>{sq}</g></svg>'
    im=QImage(W,H,QImage.Format_ARGB32); im.fill(QtCore.Qt.transparent)
    p=QPainter(im); QtSvg.QSvgRenderer(QtCore.QByteArray(svg.encode())).render(p); p.end(); return im
# Knight-Pfad
path=QPainterPath(); f=QFont("STIX Two Math"); f.setPixelSize(660); path.addText(0,0,f,"♞")
br=path.boundingRect(); s=660.0/br.height()
t=QTransform(); t.translate(512,560); t.scale(s,s); t.translate(-br.center().x(),-br.center().y())
gp=t.map(path)
# 1) Maske rendern
kn=QImage(W,H,QImage.Format_ARGB32); kn.fill(QtCore.Qt.transparent)
kp=QPainter(kn); kp.setRenderHint(QPainter.Antialiasing,False); kp.fillPath(gp, QColor("#34495f")); kp.end()
buf=bytes(kn.constBits())                       # BGRA, Alpha = i*4+3
ext=bytearray(W*H); dq=collections.deque()
def seed(i):
    if buf[i*4+3]<128 and not ext[i]: ext[i]=1; dq.append(i)
for x in range(W): seed(x); seed((H-1)*W+x)
for y in range(H): seed(y*W); seed(y*W+W-1)
while dq:
    i=dq.popleft(); x=i%W; y=i//W
    if x+1<W: j=i+1; 
    for nx,ny in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
        if 0<=nx<W and 0<=ny<H:
            j=ny*W+nx
            if not ext[j] and buf[j*4+3]<128: ext[j]=1; dq.append(j)
# 2) innere Löcher = alpha<40 und nicht exterior -> dunkel füllen
mv=kn.bits(); dark=bytes([0x5f,0x49,0x34,0xff])
n=0
for i in range(W*H):
    if buf[i*4+3]<128 and not ext[i]:
        mv[i*4:i*4+4]=dark; n+=1
print("Löcher gefüllt:", n)
# 3) Kerben (Hals-Schwung, Stirn-Locke) gezielt dunkel auffüllen (SourceOver)
def P(pts): return QPolygonF([QPointF(*p) for p in pts])
kfix=QPainter(kn); kfix.setRenderHint(QPainter.Antialiasing,True); kfix.setPen(QtCore.Qt.NoPen); kfix.setBrush(QColor("#34495f"))
kfix.drawPolygon(P([(412,308),(548,312),(590,374),(438,390)]))                 # Stirn-Locke
kfix.drawPolygon(P([(456,436),(582,450),(662,528),(666,644),(544,656),(464,646),(430,552)]))  # Hals-Schwung
kfix.drawPolygon(P([(606,432),(672,448),(664,500),(600,488)]))  # Zwickel Kopf/Mähne
kfix.drawPolygon(P([(618,474),(656,482),(650,508),(614,500)]))  # winziger Rest am Auge
kfix.end()
# 4) Facetten per SourceAtop
kp=QPainter(kn); kp.setRenderHint(QPainter.Antialiasing,True)
kp.setCompositionMode(QPainter.CompositionMode_SourceAtop); kp.setPen(QtCore.Qt.NoPen)
facets=[
 ([(450,300),(600,340),(470,445)],"#73879f"),
 ([(300,545),(452,452),(470,520)],"#647f98"),
 ([(300,545),(470,520),(345,615)],"#56708a"),
 ([(300,545),(345,615),(360,670),(300,605)],"#41596f"),
 ([(470,445),(600,470),(545,610),(455,560)],"#283b4e"),
 ([(455,560),(545,610),(430,665),(382,600)],"#223344"),
 ([(600,348),(700,402),(642,470)],"#526c85"),
 ([(642,470),(700,402),(732,560)],"#33485d"),
 ([(660,560),(735,620),(645,705)],"#223344"),
 ([(395,640),(470,640),(432,762),(368,742)],"#4d6680"),
 ([(470,640),(625,682),(602,762),(442,762)],"#283b4e"),
 ([(338,755),(692,755),(662,795),(360,795)],"#647f98"),
 ([(360,795),(662,795),(682,856),(340,856)],"#3a5066"),
 ([(520,797),(682,800),(692,860),(545,860)],"#243749"),
]
for pts,col in facets: kp.setBrush(QColor(col)); kp.drawPolygon(P(pts))
kp.end()
img=bgimg(); p=QPainter(img); p.drawImage(0,0,kn); p.end()
pathlib.Path("/tmp/icons"); img.save("/tmp/icons/facet_v11.png"); print("ok")
