## benchmark experiments for blog post

benchmarks for [categorize everything all at once](https://iev.ee/blog/categorize-everything-all-at-once/).

spaCy `en_core_web_sm` NER vs `resharp::RegexSet::categorize_all` on the same paragraph, repeated.

### dependencies

- nix (flakes)

### running

```
./run.sh [paragraphs=1000]
```

or individually:

```
nix run .#spacy -- 1000 8                  # paragraphs, processes
nix run .#resharp -- 1000                  # paragraphs, prints a thread ladder
nix run .#confidence -- "text" [--svg]     # spaCy beam-parse span probabilities
```

`RESHARP=/path/to/checkout nix run .#resharp` benches a local resharp instead of the crates.io release.

### results

Ryzen 7 5800X, 1 MB of text:

| | 1 thread | 8 threads |
|---|---|---|
| spaCy 3.8 `en_core_web_sm` | 0.09 MB/s | 0.43 MB/s |
| resharp `categorize_all`, 10 patterns | 0.36 GB/s | 1.92 GB/s |
