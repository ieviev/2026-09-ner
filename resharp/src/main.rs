use resharp::{RegexSet, TaggedMatch};
use std::time::Instant;

const PATTERNS: &[&str] = &[
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}",
    r"\$[0-9]+(?:\.[0-9]{2})?",
    r"[0-9]+(?:\.[0-9]+)?%",
    r"[a-z.]+@[a-z]+\.[a-z]+",
    r"https?://[^ ]+",
    r"[0-9]+",
    r"[A-Z][a-z]+\b&~(On|In|At|To|For|Of|The|An|And|Via|Was|Is)",
    r"[a-z]+ing\b",
    r"[a-z]+(?:ful|less|ous|ive)\b",
    r"[a-z]+ly\b",
];

const PARAGRAPH: &str = "On 2024-01-15 Alice was carefully sending $12.50 to bob.smith@example.com, \
a generous 30% tip, via https://pay.example.org/x for 3 wonderful things. The quick brown fox \
jumps over the dog while nobody watches the clock on the wall of the old house. \
It was a bright cold day in April, and the clocks were striking thirteen. Winston Smith, his chin \
nuzzled into his breast in an effort to escape the vile wind, slipped through the glass doors of \
Victory Mansions, though not enough to prevent a swirl of gritty dust from entering along with him. \
The hallway smelt of boiled cabbage and old rag mats. At one end of it a coloured poster, too large \
for indoor display, had been tacked to the wall. It depicted simply an enormous face, more than a \
metre wide: the face of a man of about forty-five, with a heavy black moustache and ruggedly handsome \
features. Winston made for the stairs. It was no use trying the lift. Even at the best of times it \
was seldom working, and at present the electric current was cut off during daylight hours.\n\n";

fn paragraph_chunks(text: &[u8], n: usize) -> Vec<(usize, usize)> {
    let mut bounds = vec![0];
    for i in 1..n {
        let mut p = text.len() * i / n;
        while p + 1 < text.len() && !(text[p] == b'\n' && text[p + 1] == b'\n') {
            p += 1;
        }
        bounds.push(p.min(text.len()));
    }
    bounds.push(text.len());
    bounds.windows(2).map(|w| (w[0], w[1])).collect()
}

fn run_parallel(sets: &[RegexSet], text: &[u8]) -> Vec<Vec<TaggedMatch>> {
    let chunks = paragraph_chunks(text, sets.len());
    std::thread::scope(|s| {
        let handles: Vec<_> = chunks
            .iter()
            .zip(sets)
            .map(|(&(lo, hi), set)| {
                s.spawn(move || {
                    let mut v = set.categorize_all(&text[lo..hi]).unwrap();
                    for m in &mut v {
                        m.start += lo;
                        m.end += lo;
                    }
                    v
                })
            })
            .collect();
        handles.into_iter().map(|h| h.join().unwrap()).collect()
    })
}

fn timed(text: &[u8], mut f: impl FnMut() -> Vec<Vec<TaggedMatch>>) -> (f64, Vec<Vec<TaggedMatch>>) {
    let mut out = f();
    let t = Instant::now();
    let mut reps = 0;
    while t.elapsed().as_secs_f64() < 1.0 {
        out = f();
        reps += 1;
    }
    ((text.len() * reps) as f64 / t.elapsed().as_secs_f64() / 1e9, out)
}

fn cpu_model() -> String {
    std::fs::read_to_string("/proc/cpuinfo")
        .ok()
        .and_then(|s| {
            s.lines()
                .find(|l| l.starts_with("model name"))
                .and_then(|l| l.split(':').nth(1))
                .map(|m| m.trim().to_string())
        })
        .unwrap_or_else(|| "unknown cpu".to_string())
}

fn main() {
    let paragraphs: usize = std::env::args().nth(1).map_or(1000, |a| a.parse().unwrap());
    let text: Vec<u8> = PARAGRAPH.repeat(paragraphs).into_bytes();
    let cores = std::thread::available_parallelism().map_or(1, |c| c.get());

    println!("{}", cpu_model());
    println!("{cores} hardware threads, avx2 compiled: {}, avx2 detected: {}", cfg!(target_feature = "avx2"), std::arch::is_x86_feature_detected!("avx2"));
    println!("{:.1} MB of text ({paragraphs} paragraphs), {} patterns\n", text.len() as f64 / 1e6, PATTERNS.len());

    let set = RegexSet::new(PATTERNS).unwrap();
    let (gbs, single) = timed(&text, || vec![set.categorize_all(&text).unwrap()]);
    let single = &single[0];
    println!("{:>3} thread  {gbs:>6.2} GB/s   {} matches (1 per {:.0} bytes)", 1, single.len(), text.len() as f64 / single.len() as f64);

    let mut ladder: Vec<usize> = [2, 4, 8, 12, 16, 24, 32, 48, 64, 96, 128].into_iter().filter(|&t| t <= cores * 2).collect();
    if !ladder.contains(&cores) {
        ladder.push(cores);
        ladder.sort_unstable();
    }
    let mut best = 0.0;
    for threads in ladder {
        let sets: Vec<RegexSet> = (0..threads).map(|_| RegexSet::new(PATTERNS).unwrap()).collect();
        let (gbs, par) = timed(&text, || run_parallel(&sets, &text));
        assert!(par.iter().flatten().eq(single.iter()));
        println!("{threads:>3} threads {gbs:>6.2} GB/s");
        if gbs < best {
            break;
        }
        best = gbs;
    }
}
