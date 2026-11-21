"""Regenerate the original, non-vendor wordmark. Requires Pillow, not HA runtime."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
target=ROOT/'custom_components/apc_direct/brand'
target.mkdir(parents=True,exist_ok=True)
for side,name in ((256,'icon.png'),(512,'icon@2x.png')):
    image=Image.new('RGBA',(side,side),(0,0,0,0));draw=ImageDraw.Draw(image)
    inset=side//20
    draw.rounded_rectangle((inset,inset,side-inset,side-inset),radius=side//9,fill='#087d74')
    draw.text((side/2,side*.40),'UPS',font=ImageFont.load_default(size=side//4),anchor='mm',fill='white')
    draw.line((side*.24,side*.60,side*.76,side*.60),fill='#b9e2dc',width=max(1,side//80))
    draw.text((side/2,side*.76),'USB',font=ImageFont.load_default(size=side//7),anchor='mm',fill='white')
    image.save(target/name,optimize=True)
