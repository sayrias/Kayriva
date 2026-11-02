"""Rebuild the README SVGs with the bundled Noto Sans font: python3 docs/assets/generate.py."""
from pathlib import Path
from html import escape
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QFontDatabase, QPainterPath
app=QApplication([])
root=Path(__file__).resolve().parents[2]
QFontDatabase.addApplicationFont(str(root/'src/ai_studio/ui/assets/NotoSans-Regular.ttf'))
out=Path(__file__).resolve().parent;out.mkdir(parents=True,exist_ok=True)
ink='#ececf1'; muted='#a5a9b6';accent='#c9bcec';edge='#383c48';base='#15171c';surface='#22252d'
def text(s,x,y,size=20,color=ink,weight=400):
    font=QFont('Noto Sans');font.setPixelSize(size);font.setWeight(QFont.Weight(weight))
    p=QPainterPath();p.addText(x,y,font,s)
    a=[];i=0
    while i<p.elementCount():
        e=p.elementAt(i)
        if e.isMoveTo():a.append(f'M{e.x:.2f} {e.y:.2f}')
        elif e.isLineTo():a.append(f'L{e.x:.2f} {e.y:.2f}')
        elif e.type==QPainterPath.ElementType.CurveToElement:
            b=p.elementAt(i+1);c=p.elementAt(i+2);a.append(f'C{e.x:.2f} {e.y:.2f} {b.x:.2f} {b.y:.2f} {c.x:.2f} {c.y:.2f}');i+=2
        i+=1
    return f'<g aria-label="{escape(s,quote=True)}"><path fill="{color}" d="{" ".join(a)}"/></g>'
def svg(name,w,h,title,desc,body):
    (out/name).write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="title desc"><title id="title">{escape(title)}</title><desc id="desc">{escape(desc)}</desc>{body}</svg>\n')
def mark(x,y,scale,color=accent,width=1.5):
    return f'<g transform="translate({x} {y}) scale({scale})" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round"><path d="M4 19V9l8-6 8 6v10M8 17V11l4-3 4 3v6M4 19l8-6 8 6M12 13v8"/></g>'
body=f'<rect x="1" y="1" width="1118" height="358" rx="20" fill="{base}" stroke="{edge}"/>'
body+='<defs><clipPath id="frame"><rect x="1" y="1" width="1118" height="358" rx="20"/></clipPath></defs><g clip-path="url(#frame)">'
body+=text('Kayriva',48,114,79)
body+=text('Your model, local.',52,184,31,accent)+text('Your own workspace.',52,225,31)
body+=f'<path d="M52 270H636" stroke="{edge}"/>'
body+=text('Chat',52,309,18,muted)+text('Project files',168,309,18,muted)+text('Tools',364,309,18,muted)
body+=f'<g fill="{accent}"><circle cx="145" cy="303" r="2"/><circle cx="342" cy="303" r="2"/></g>'
# The product emblem is the composition: nested paths are a clear, flat vector mark.
body+=f'<path d="M724 360V122l172-126 172 126v238" stroke="#2a2c36" stroke-width="1.2" fill="none"/>'
body+=f'<path d="M750 360V139L896 32l146 107v221" stroke="#33313f" stroke-width="1.2" fill="none"/>'
body+=mark(777,84,10,accent,0.85)
body+=text('LOCAL DESKTOP',783,314,15,muted)+'</g>'
svg('kayriva-banner.svg',1120,360,'Kayriva — your model, local. Your own workspace.','Kayriva wordmark and lavender geometric emblem on graphite. Chat, project files and tools in one desktop workspace.',body)
for name,title,sub,icon in [('start','Get started','Setup and your first chat','play'),('models','Choose a model','Catalog and hardware guide','layers'),('develop','Build with Kayriva','Architecture, tools and builds','code')]:
    b=f'<rect x="1" y="1" width="350" height="86" rx="12" fill="{surface}" stroke="{edge}"/>'
    paths={'play':'M21 26l12 8-12 8Z','layers':'m26 23 12 7-12 7-12-7Zm-12 14 12 7 12-7m-24 7 12 7 12-7','code':'m20 26-8 9 8 9m14-18 8 9-8 9m-5-22-5 26'}
    b+=f'<g transform="translate(4 7)" fill="none" stroke="{accent}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="{paths[icon]}"/></g>'
    b+=text(title,66,36,20)+text(sub,66,62,12,muted)
    b+=f'<path d="M316 38l6 6-6 6m-9-6h15" fill="none" stroke="{accent}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>'
    svg(f'nav-{name}.svg',352,88,title,sub,b)
# Honest architecture diagram, not a fabricated application screenshot.
b=f'<rect x="1" y="1" width="1118" height="178" rx="16" fill="{base}" stroke="{edge}"/>'
for x,title,sub in [(36,'Your files','Projects · documents · images'),(414,'Kayriva','Chat · plans · selected tools'),(803,'Local model','llama.cpp · CPU / GPU / RAM')]:
    b+=text(title,x,66,25,accent if title=='Kayriva' else ink)+text(sub,x,100,15,muted)
for x in [334,722]:b+=f'<path d="M{x} 76h38m-8-6 8 6-8 6" fill="none" stroke="{muted}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>'
b+=f'<path d="M36 128h1048" stroke="{edge}"/>'+text('Web and MCP connections participate only in the workflows you enable.',36,157,14,muted)
svg('local-workflow.svg',1120,180,'Kayriva local workflow','Your files connect to a local model through Kayriva. Web and MCP connections participate only in the workflows you enable.',b)
