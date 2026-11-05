"""Fix the Phase 3 subset before any Phase 1 result is known: 4 test samples per class (20 total), stratified,
always including #31 (class 2) and #81 (class 5); the rest drawn with numpy default_rng(2026).
-> summary/phase3_subset.json"""
import json
import numpy as np
import common as C

if __name__ == "__main__":
    rng = np.random.default_rng(2026); y = C.YTE; must = {1: [31], 4: [81]}
    sub = []
    for c in range(5):
        pool = [i for i in range(90) if y[i] == c and i not in must.get(c, [])]
        sub += must.get(c, []) + sorted(rng.choice(pool, 4 - len(must.get(c, [])), replace=False).tolist())
    sub = sorted(int(i) for i in sub)
    (C.CAMP / "summary/phase3_subset.json").write_text(json.dumps(dict(subset=sub, labels=[int(y[i]) + 1 for i in sub]), indent=1))
    print(sub, [int(y[i]) + 1 for i in sub])
