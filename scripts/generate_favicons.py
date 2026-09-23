"""Generate AI FAQ College Chat Bot favicon / app icons.

Draws the logo mark (graduation cap + chat bubble + three AI dots) at high
resolution with Pillow and downsamples for crisp small-size icons.
"""
from PIL import Image, ImageDraw
import os

OUT = os.path.join(os.path.dirname(__file__), "..", "apps", "user-web", "public")

BG = (7, 7, 10, 255)          # near-black background
SURFACE = (238, 242, 251, 255)  # light bubble / cap
INNER = (11, 11, 14, 255)     # dark inner bubble
BLUE = (59, 130, 246, 255)    # AI blue dots

S = 4  # supersample factor
W = 512 * S


def rounded(draw, box, radius, fill):
    draw.rounded_rectangle(box, radius=radius, fill=fill)


def make_icon(with_bg=True):
    img = Image.new("RGBA", (W, W), BG if with_bg else (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    s = S
    # ── graduation cap (mortarboard) ──
    cap_pts = [(256 * s, 88 * s), (436 * s, 184 * s), (256 * s, 280 * s), (76 * s, 184 * s)]
    d.polygon(cap_pts, fill=SURFACE)
    # cap base band (small trapezoid under the board)
    d.polygon([(196 * s, 272 * s), (316 * s, 272 * s), (300 * s, 300 * s), (212 * s, 300 * s)],
              fill=SURFACE)
    # tassel: cord + knob
    d.line([(430 * s, 188 * s), (430 * s, 306 * s)], fill=SURFACE, width=9 * s)
    d.ellipse([(414 * s, 302 * s), (446 * s, 334 * s)], fill=BLUE)

    # ── chat bubble ──
    rounded(d, [(140 * s, 300 * s), (372 * s, 452 * s)], 52 * s, SURFACE)
    # tail
    d.polygon([(196 * s, 440 * s), (176 * s, 496 * s), (250 * s, 448 * s)], fill=SURFACE)
    # dark inner
    rounded(d, [(166 * s, 326 * s), (346 * s, 426 * s)], 34 * s, INNER)
    # three AI dots
    for cx in (206, 256, 306):
        d.ellipse([(cx * s - 15 * s, 351 * s), (cx * s + 15 * s, 381 * s)], fill=BLUE)

    # ── downsample ──
    final = img.resize((512, 512), Image.LANCZOS)
    return final


def main():
    os.makedirs(OUT, exist_ok=True)
    icon = make_icon(with_bg=True)

    icon.resize((512, 512), Image.LANCZOS).save(os.path.join(OUT, "ai-faq-college-chat-bot-icon.png"))
    icon.resize((192, 192), Image.LANCZOS).save(os.path.join(OUT, "icon-192.png"))
    icon.resize((512, 512), Image.LANCZOS).save(os.path.join(OUT, "icon-512.png"))
    # apple touch icon: solid bg (iOS flattens transparency anyway)
    icon.resize((180, 180), Image.LANCZOS).save(os.path.join(OUT, "apple-touch-icon.png"))
    # favicon: compact dark square
    icon.resize((64, 64), Image.LANCZOS).save(os.path.join(OUT, "favicon.png"))
    print("icons written to", OUT)


if __name__ == "__main__":
    main()