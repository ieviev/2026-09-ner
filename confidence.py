import sys, spacy
from collections import defaultdict

args = [a for a in sys.argv[1:] if not a.startswith("--")]
text = args[0] if args else (
    "On 2024-01-15 Alice was carefully sending $12.50 to bob.smith@example.com, "
    "a generous 30% tip, via https://pay.example.org/x for 3 wonderful things.")
svg = "--svg" in sys.argv
width = 16

nlp = spacy.load("en_core_web_sm", exclude=["tagger", "parser", "attribute_ruler", "lemmatizer"])
ner = nlp.get_pipe("ner")
doc = nlp.make_doc(text)
for name, proc in nlp.pipeline:
    if name != "ner":
        doc = proc(doc)
scores = defaultdict(float)
for beam in ner.beam_parse([doc], beam_width=width, beam_density=0.0001):
    for score, ents in ner.moves.get_beam_parses(beam):
        for start, end, label in ents:
            scores[(doc[start].idx, doc[end - 1].idx + len(doc[end - 1]), label)] += score
ranked = sorted(scores.items(), key=lambda kv: -kv[1])

if not svg:
    print(f"spacy {spacy.__version__}, en_core_web_sm, greedy:")
    for e in nlp(text).ents:
        print(f"         {e.label_:<12} {e.text}")
    print(f"beam_parse(beam_width={width}):")
    for (s, e, label), p in ranked:
        print(f"  {p:6.3f} {label:<12} {text[s:e]}")
    sys.exit()

COLORS = {"DATE": "#d7af5f", "PERCENT": "#87af87", "CARDINAL": "#5f87af", "ORG": "#af87d7",
          "PERSON": "#af87d7", "MONEY": "#87af87", "TIME": "#afaf5f"}
spans = []
for (s, e, label), p in ranked:
    if p < 0.3 or any(not (e <= a or s >= b) for a, b, _, _ in spans):
        continue
    spans.append((s, e, label, p))

CW, X0, COLS, PITCH = 9.2, 20.0, 53, 52
lines, pos = [], 0
while pos < len(text):
    end = min(pos + COLS, len(text))
    if end < len(text):
        cut = text.rfind(" ", pos, end + 1)
        if cut > pos:
            end = cut + 1
    lines.append((pos, end))
    pos = end
W = int(X0 * 2 + max(e - s for s, e in lines) * CW)
H = 30 + PITCH * len(lines)
out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" style="max-width:{int(W * 640 / 527)}px;display:block;margin:1.5em auto;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace">']
def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;")
for li, (ls, le) in enumerate(lines):
    y = 36 + PITCH * li
    label_end = -1e9
    for s, e, label, p in sorted(spans):
        a, b = max(s, ls), min(e, le)
        while b > a and text[b - 1] == " ":
            b -= 1
        if a >= b:
            continue
        x = X0 + (a - ls) * CW - 3
        w = (b - a) * CW + 6
        c = COLORS.get(label, "#888888")
        out.append(f'  <rect x="{x:.1f}" y="{y-14}" width="{w:.1f}" height="23" rx="4" fill="{c}" fill-opacity="0.22" stroke="{c}" stroke-opacity="0.6"/>')
        if a == s:
            tag = f"{label} {p*100:.1f}%"
            ly = y - 19 if x + 3 >= label_end else y + 19
            if ly < y:
                label_end = x + 3 + len(tag) * 5.6 + 6
            out.append(f'  <text x="{x+3:.1f}" y="{ly}" font-size="8" fill="{c}" letter-spacing="0.6">{tag}</text>')
    seg = text[ls:le]
    out.append(f'  <text x="{X0}" y="{y}" font-size="15" xml:space="preserve" textLength="{len(seg)*CW:.1f}" lengthAdjust="spacingAndGlyphs" fill="currentColor">{esc(seg)}</text>')
out.append("</svg>")
print("\n".join(out))
