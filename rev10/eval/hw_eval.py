import numpy as np, sys
from hw_retrain import dies, accuracy, Xte, yte, Xtr, ytr, F0
Fs = {"original": F0, "hw-trained": np.load(sys.argv[1]).astype(int)}
for m in (4, 8):
    cs20, dl20 = dies(1000, 0.020, 101); cs50, dl50 = dies(1000, 0.050, 202)
    for name, F in Fs.items():
        sw = (np.argmax(Xte @ F, 1) == yte).mean()
        a20 = accuracy(F, Xte, yte, cs20, dl20, m); a50 = accuracy(F, Xte, yte, cs50, dl50, m)
        tr = accuracy(F, Xtr, ytr, cs50[:1], dl50[:1], m)[0]
        print(f"m={m} {name:10s} | software {sw*100:5.1f}% | HW nominal test {a50[0]*100:5.1f}% (train {tr*100:.1f}%) | "
              f"sigma20 mean {a20[1:].mean()*100:5.1f}% p5 {np.percentile(a20[1:],5)*100:5.1f}% | sigma50 mean {a50[1:].mean()*100:5.1f}% p5 {np.percentile(a50[1:],5)*100:5.1f}%")
