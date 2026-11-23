"""Render the repository's distributable v4 deck for the in-browser slide viewer.

Python 3.10+, python-pptx, PyMuPDF and Pillow; LibreOffice for PPTX -> PDF.
Only the public *_repo.pptx is read. Original inputs are never modified.
Use --pdf inventory_site/dist/resources/slides_v4.pdf to rerender the saved PDF.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile

import fitz
from PIL import Image, __version__ as pillow_version
from pptx import Presentation
import pptx

ROOT=Path(__file__).resolve().parents[2]
SITE=ROOT/"inventory_site"
SOURCE=ROOT/"presentation/Gong_Simchi_2024_Academic_60min_v4_repo.pptx"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def title_and_text(slide, index):
    candidates=[]
    for shape in slide.shapes:
        if not shape.has_text_frame or not shape.text.strip():
            continue
        sizes=[r.font.size.pt for p in shape.text_frame.paragraphs for r in p.runs if r.font.size]
        candidates.append((max(sizes,default=0),-shape.top,shape.text.strip()))
    title=(slide.shapes.title.text.strip() if slide.shapes.title and slide.shapes.title.text.strip()
           else max(candidates,default=(0,0,f"Slide {index}"))[2])
    return title.replace('\n',' '), '\n\n'.join(
        shape.text.strip() for shape in sorted(slide.shapes,key=lambda s:(s.top,s.left))
        if shape.has_text_frame and shape.text.strip())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf',type=Path,help='Use an existing PDF exported from the distributable deck.')
    parser.add_argument('--width',type=int,default=1600)
    args=parser.parse_args()
    if not 1000<=args.width<=2400:parser.error('width must be 1000–2400')
    deck=Presentation(SOURCE)
    resources=SITE/'dist/resources';resources.mkdir(exist_ok=True,parents=True)
    pdf=resources/'slides_v4.pdf'
    renderer='saved PDF'
    if args.pdf:
        if args.pdf.resolve()!=pdf.resolve():shutil.copyfile(args.pdf,pdf)
        previous=resources/'slides_manifest.json'
        if previous.exists():
            prior=json.loads(previous.read_text())
            if prior.get('pdf',{}).get('sha256')==sha(pdf):
                if prior['source']['sha256']!=sha(SOURCE):
                    raise ValueError('Saved PDF belongs to an older PPTX; export the current deck first.')
                renderer=prior['software']['pdf_export']
    else:
        with tempfile.TemporaryDirectory(prefix='gong-slides-') as directory:
            temp=Path(directory)
            env=os.environ.copy();env['XDG_CACHE_HOME']=str(temp/'cache')
            command=['soffice','-env:UserInstallation='+(temp/'profile').as_uri(),'--headless',
                     '--convert-to','pdf','--outdir',str(temp),str(SOURCE)]
            result=subprocess.run(command,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,check=True)
            print(result.stdout.strip(),flush=True)
            shutil.copyfile(temp/(SOURCE.stem+'.pdf'),pdf)
            renderer=subprocess.check_output(['soffice','--version'],text=True).strip()
    document=fitz.open(pdf)
    if len(document)!=len(deck.slides):raise ValueError('PDF page count differs from PPTX slide count')
    target=SITE/'dist/media/slides';target.mkdir(parents=True,exist_ok=True)
    slides=[]
    for i,(page,slide) in enumerate(zip(document,deck.slides),start=1):
        pix=page.get_pixmap(matrix=fitz.Matrix(args.width/page.rect.width,args.width/page.rect.width),alpha=False)
        image=Image.frombytes('RGB',[pix.width,pix.height],pix.samples)
        name=f'slide_{i:02}.webp';thumb=f'thumb_{i:02}.webp'
        image.save(target/name,'WEBP',lossless=True,method=6)
        image.thumbnail((240,135),Image.Resampling.LANCZOS)
        image.save(target/thumb,'WEBP',quality=86,method=6)
        title,text=title_and_text(slide,i)
        slides.append({'number':i,'title':title,'text':text,'image':'./media/slides/'+name,
                       'thumbnail':'./media/slides/'+thumb,'width':pix.width,'height':pix.height,
                       'image_sha256':sha(target/name),'thumbnail_sha256':sha(target/thumb)})
    manifest={'schema_version':1,'title':'Gong & Simchi-Levi · Academic presentation v4',
              'source':{'path':str(SOURCE.relative_to(ROOT)),'sha256':sha(SOURCE),'scope':'distributable repo deck; original third-party screenshots already replaced'},
              'pdf':{'path':'./resources/slides_v4.pdf','sha256':sha(pdf)},'count':len(slides),
              'software':{'python':platform.python_version(),'python_pptx':pptx.__version__,
                          'pymupdf':fitz.VersionBind,'pillow':pillow_version,'pdf_export':renderer},
              'slides':slides}
    (resources/'slides_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Rendered {len(slides)} slides and thumbnails; source and asset SHA-256 recorded.',flush=True)


if __name__=='__main__':main()
