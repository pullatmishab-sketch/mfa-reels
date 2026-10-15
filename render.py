#!/usr/bin/env python3
"""MFA reel renderer: text -> 1080x1920 mp4 (burgundy bg + header + serif text + audio)."""
import sys, os, subprocess, argparse, tempfile
from PIL import Image, ImageDraw, ImageFont, ImageFilter
D = os.path.dirname(os.path.abspath(__file__))
A = lambda *p: os.path.join(D, *p)
FONT = lambda n: next(x for x in (A('fonts', n), '/usr/share/fonts/truetype/liberation/' + n, '/usr/share/fonts/liberation-fonts/' + n) if os.path.exists(x))
W, H = 1080, 1920
CFG = dict(
    name="Muslim Family Academy", handle="@muslimfamilyacademy",
    logo_x=227, logo_d=98, top=460,          # header geometry (matched to reference)
    name_w=322, handle_w=262,                # target pixel widths -> font sizes
    body_x=244, body_ref_w=612, pitch=44.4, max_w=640, body_gap=29,
    center_y=881, max_lines=20, min_scale=0.62,
    duration=None, fade=0.45, audio_fade=0.6)

def font_to_width(path, text, width):
    lo, hi = 8, 200
    while hi - lo > 0.25:
        mid = (lo + hi) / 2
        if ImageFont.truetype(path, mid).getlength(text) > width: hi = mid
        else: lo = mid
    return lo

def wrap(text, font, maxw):
    lines = []
    for para in text.replace('\\n', '\n').split('\n'):
        words, cur = para.split(' '), ''
        if not para.strip(): lines.append(''); continue
        for w in words:
            t = (cur + ' ' + w).strip()
            if cur and font.getlength(t) > maxw: lines.append(cur); cur = w
            else: cur = t
        lines.append(cur)
    return lines

def overlay(text, out_png):
    c = CFG
    serif, sansb, sans = FONT('LiberationSerif-Regular.ttf'), FONT('LiberationSans-Bold.ttf'), FONT('LiberationSans-Regular.ttf')
    base = font_to_width(serif, "In youth, a marriage runs on mawaddah.", c['body_ref_w'])
    scale = 1.0
    while True:
        bf = ImageFont.truetype(serif, base * scale); pitch = c['pitch'] * scale
        lines = wrap(text, bf, c['max_w'])
        if len(lines) <= c['max_lines'] or scale <= c['min_scale']: break
        scale -= 0.04
    header_h = c['logo_d']; body_h = c['body_gap'] + len(lines) * pitch
    top = int(c['center_y'] - (header_h + body_h) / 2)
    top = max(top, 330)  # keep clear of IG top bar
    img = Image.new('RGBA', (W * 2, H * 2), (0, 0, 0, 0)); S = 2   # 2x supersample
    d = ImageDraw.Draw(img)
    logo = Image.open(A('logo.jpg')).convert('RGBA').resize((c['logo_d'] * S,) * 2, Image.LANCZOS)
    m = Image.new('L', logo.size, 0); ImageDraw.Draw(m).ellipse((0, 0, logo.size[0] - 1, logo.size[1] - 1), fill=255); logo.putalpha(m)
    img.alpha_composite(logo, (c['logo_x'] * S, top * S))
    nf = ImageFont.truetype(sansb, font_to_width(sansb, c['name'], c['name_w']) * S)
    hf = ImageFont.truetype(sans, font_to_width(sans, c['handle'], c['handle_w']) * S)
    nx = c['logo_x'] + c['logo_d'] + 16
    d.text((nx * S, (top + 6) * S), c['name'], font=nf, fill=(255, 255, 253, 255))
    d.text((nx * S, (top + 55) * S), c['handle'], font=hf, fill=(255, 250, 251, 255))
    bd = int(c['name_w'] * 0.0 + 33) ; badge = Image.open(A('badge.png')).convert('RGBA').resize((bd * S, bd * S), Image.LANCZOS)
    img.alpha_composite(badge, (int((nx + c['name_w'] + 8) * S), int((top + 5) * S)))
    bf2 = ImageFont.truetype(serif, base * scale * S)
    y = top + header_h + c['body_gap']
    for ln in lines:
        d.text((c['body_x'] * S, y * S), ln, font=bf2, fill=(255, 254, 253, 255)); y += pitch
    img.resize((W, H), Image.LANCZOS).save(out_png)

def render(text, out_mp4, audio=None, bg=None, duration=None):
    c = CFG; audio = audio or A('bg1.mp3'); bg = bg or A('bg.jpg')
    if duration is None:
        duration = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', audio]).decode().strip())
    with tempfile.TemporaryDirectory() as t:
        ov = os.path.join(t, 'ov.png'); overlay(text, ov)
        fc = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1[b];"
              f"[1:v]format=rgba,fade=t=in:st=0:d={c['fade']}:alpha=1[o];[b][o]overlay,format=yuv420p[v];"
              f"[2:a]afade=t=out:st={duration-c['audio_fade']:.2f}:d={c['audio_fade']},atrim=0:{duration:.2f}[a]")
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-loop', '1', '-framerate', '30', '-i', bg, '-loop', '1', '-framerate', '30', '-i', ov, '-i', audio,
                        '-filter_complex', fc, '-map', '[v]', '-map', '[a]', '-t', f'{duration:.2f}', '-r', '30', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20',
                        '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', out_mp4], check=True)
    return out_mp4

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('text'); p.add_argument('out'); p.add_argument('--png', action='store_true')
    a = p.parse_args()
    if a.png: overlay(a.text, a.out)
    else: render(a.text, a.out)
