#!/usr/bin/env python3
"""Subset the self-hosted display fonts for aquora.cn (mainland: no Google Fonts).

Usage: python3 tools/subset_fonts.py <built_site_dir> [fonts_src_dir]
- Scans every .html in the built site, collects the characters that appear inside
  elements that use the display serif (class contains 'serif' / 'display', or h1/h2/h3/
  blockquote/.hero/.manifesto), plus a safety set (digits, ASCII, CJK punctuation,
  the archetype names, and the 300 most frequent characters of the whole site),
  plus every character of assets/fonts/subset-extra.txt — copy that lives in JS strings /
  data-* attributes / placeholders that the HTML scan cannot see (e.g. cn/reserve.html's
  four whispers). Keep that file in sync when such copy changes.
- Writes assets/fonts/AquoraSerifSC.woff2 (Noto Serif SC, variable wght),
  assets/fonts/AquoraCormorant.woff2 and AquoraCormorant-Italic.woff2 (Cormorant Garamond, variable).
Licenses: SIL OFL 1.1 (copies in assets/fonts/OFL-*.txt).
- Layout features kept: kern,liga,calt,onum,pnum,tnum,ss01 + locl. `locl` matters for Noto Serif SC:
  under lang=zh (ZHS langsys) it swaps the proportional Latin em dash U+2014 (advance 874, ink sits at the
  Latin baseline) for uni2015 (full-width, vertically centred on the CJK body) — without it 「——」 renders as
  two short, low bars with a gap (cn/reserve.html fourth whisper). In our subset locl only touches ", ' and —.
"""
import sys, re, pathlib, html, collections, subprocess
site = pathlib.Path(sys.argv[1]); src = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else '/private/tmp/claude-502/-Users-abel-Downloads-Aquora/f80d369c-273a-4810-a155-0c77dbc6b236/scratchpad/fonts-src')
root = pathlib.Path(__file__).resolve().parent.parent
out = root / 'assets' / 'fonts'; out.mkdir(parents=True, exist_ok=True)
serif_chars, freq = set(), collections.Counter()
tag_re = re.compile(r'<(h1|h2|h3|blockquote|p|span|div|a|em|strong|li|figcaption|cite)([^>]*)>(.*?)</\1>', re.S | re.I)
for f in site.rglob('*.html'):
    t = f.read_text('utf-8', errors='ignore')
    text = html.unescape(re.sub(r'<script.*?</script>|<style.*?</style>', '', t, flags=re.S))
    freq.update(ch for ch in re.sub(r'<[^>]+>', '', text) if '㐀' <= ch <= '鿿')
    for m in tag_re.finditer(text):
        tag, attrs, inner = m.group(1).lower(), m.group(2), m.group(3)
        if tag in ('h1','h2','h3','blockquote') or re.search(r'class="[^"]*(serif|display|hero|manifesto|quote|lede|tagline|han|lbl|axis-label|axis-lbl|axis-line|seal|go-han|salute|numeral|cue|whisper|stamp|rs-line|footer-icp-brand|wordmark|masthead-link|fine|zh\b)', attrs):
            serif_chars.update(html.unescape(re.sub(r'<[^>]+>', '', inner)))
    # Second pass: headings and display-class elements matched directly, so a heading nested inside a
    # <div>/<li> wrapper (the naive tag_re above stops at the wrapper's first closing tag) is not skipped.
    for m in re.finditer(r'<(h1|h2|h3|blockquote)\b[^>]*>(.*?)</\1>', text, re.S | re.I):
        serif_chars.update(html.unescape(re.sub(r'<[^>]+>', '', m.group(2))))
    for m in re.finditer(r'<(span|p|a|li|div)\b[^>]*class="[^"]*(?:serif|display|hero|manifesto|quote|lede|tagline|han|lbl|axis-label|axis-lbl|axis-line|seal|go-han|salute|numeral|cue|whisper|stamp|rs-line|footer-icp-brand|wordmark|masthead-link|fine|zh\b)[^"]*"[^>]*>(.*?)</\1>', text, re.S | re.I):
        serif_chars.update(html.unescape(re.sub(r'<[^>]+>', '', m.group(2))))
serif_chars.update(ch for ch, _ in freq.most_common(300))
serif_chars.update('0123456789，。、；：？！「」『』（）《》—…·—–‘’“”％℃')
serif_chars.update(chr(c) for c in range(0x20, 0x7f))
# extra copy that the HTML scan cannot reach (JS arrays, data-* attributes, placeholders)
extra = out / 'subset-extra.txt'
if extra.exists():
    for line in extra.read_text('utf-8').splitlines():
        if line.startswith('#'): continue   # comment lines
        serif_chars.update(ch for ch in line if not ch.isspace())
# archetype names are always displayed in serif
arche = root / '_data' / 'archetypes.yml'
if arche.exists():
    for m in re.finditer(r'(name_zh|tagline_zh):\s*"([^"]+)"', arche.read_text('utf-8')):
        serif_chars.update(m.group(2))
cjk = ''.join(sorted(c for c in serif_chars if ord(c) > 0x7f))
latin = ''.join(chr(c) for c in range(0x20, 0x7f)) + '‘’“”–—…·•€£'
(out / 'subset-chars.txt').write_text(cjk, 'utf-8')
def run(src_name, dst_name, text, extra=()):
    subprocess.run(['pyftsubset', str(src / src_name), f'--text={text}', '--flavor=woff2', '--layout-features=kern,liga,calt,onum,pnum,tnum,ss01,locl', '--no-hinting', '--desubroutinize', f'--output-file={out / dst_name}', *extra], check=True)
    print(dst_name, (out / dst_name).stat().st_size // 1024, 'KB')
run('NotoSerifSC[wght].ttf', 'AquoraSerifSC.woff2', cjk + latin)
run('CormorantGaramond[wght].ttf', 'AquoraCormorant.woff2', latin)
run('CormorantGaramond-Italic[wght].ttf', 'AquoraCormorant-Italic.woff2', latin)
print('serif chars:', len(cjk))
