"""Local benchmark: play agent A vs agent B over many seeds, both sides."""
import sys, os, time, contextlib

@contextlib.contextmanager
def quiet():
    with open(os.devnull, 'w') as dn:
        old = os.dup(2); os.dup2(dn.fileno(), 2)
        try: yield
        finally: os.dup2(old, 2); os.close(old)

with quiet():
    from kaggle_environments import make

def play(a, b, seed):
    with quiet():
        env = make('crawl', configuration={'randomSeed': seed})
        env.run([a, b])
    s = env.steps[-1]
    return s[0]['reward'], s[1]['reward']

def bench(a, b, n=20):
    aw = bw = draw = 0
    margins = []
    for seed in range(n):
        # A as player0
        ra, rb = play(a, b, seed)
        margins.append((ra or 0) - (rb or 0))
        if (ra or 0) > (rb or 0): aw += 1
        elif (rb or 0) > (ra or 0): bw += 1
        else: draw += 1
        # A as player1 (swap sides, same seed)
        rb2, ra2 = play(b, a, seed)
        margins.append((ra2 or 0) - (rb2 or 0))
        if (ra2 or 0) > (rb2 or 0): aw += 1
        elif (rb2 or 0) > (ra2 or 0): bw += 1
        else: draw += 1
    g = n * 2
    print(f"{a} vs {b}: {g} games")
    print(f"  A wins: {aw} ({100*aw/g:.0f}%) | B wins: {bw} ({100*bw/g:.0f}%) | draws: {draw}")
    print(f"  avg reward margin (A - B): {sum(margins)/len(margins):+.0f}")
    return aw, bw, draw

if __name__ == '__main__':
    A = sys.argv[1] if len(sys.argv) > 1 else 'main.py'
    B = sys.argv[2] if len(sys.argv) > 2 else 'baseline_main.py'
    N = int(sys.argv[3]) if len(sys.argv) > 3 else 20
    t = time.time()
    bench(A, B, N)
    print(f"  ({time.time()-t:.0f}s total)")
