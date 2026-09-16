import time, sys, multiprocessing, spacy
para = ("On 2024-01-15 Alice was carefully sending $12.50 to bob.smith@example.com, "
"a generous 30% tip, via https://pay.example.org/x for 3 wonderful things. The quick brown fox "
"jumps over the dog while nobody watches the clock on the wall of the old house. "
"It was a bright cold day in April, and the clocks were striking thirteen. Winston Smith, his chin "
"nuzzled into his breast in an effort to escape the vile wind, slipped through the glass doors of "
"Victory Mansions, though not enough to prevent a swirl of gritty dust from entering along with him. "
"The hallway smelt of boiled cabbage and old rag mats. At one end of it a coloured poster, too large "
"for indoor display, had been tacked to the wall. It depicted simply an enormous face, more than a "
"metre wide: the face of a man of about forty-five, with a heavy black moustache and ruggedly handsome "
"features. Winston made for the stairs. It was no use trying the lift. Even at the best of times it "
"was seldom working, and at present the electric current was cut off during daylight hours.\n\n")
n = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
procs = int(sys.argv[2]) if len(sys.argv) > 2 else 8
docs = [para] * n
total = sum(len(d.encode()) for d in docs)
print(f"spacy {spacy.__version__}, en_core_web_sm, {total/1e6:.1f} MB ({n} paragraphs)")

def run(label, nlp, n_process=1):
    nlp(para)
    t = time.perf_counter()
    ents = 0
    for doc in nlp.pipe(docs, batch_size=64, n_process=n_process):
        ents += len(doc.ents)
    dt = time.perf_counter() - t
    print(f"{label:<28} {total/dt/1e6:>8.2f} MB/s   {ents} entities")

if __name__ == "__main__":
  multiprocessing.set_start_method("fork")
  ner_only = spacy.load("en_core_web_sm", exclude=["tagger", "parser", "attribute_ruler", "lemmatizer"])
  run("ner only, 1 process", ner_only)
  run(f"ner only, {procs} processes", ner_only, procs)
  full = spacy.load("en_core_web_sm")
  run("full pipeline, 1 process", full)
  run(f"full pipeline, {procs} processes", full, procs)
  doc = full(para)
  print([(e.text, e.label_) for e in doc.ents][:12])
