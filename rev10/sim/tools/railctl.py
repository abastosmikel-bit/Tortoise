"""Replace the negative control levels with rail-to-rail (0 / 3.3 V) levels, same timing."""
import re
REPL = {
 "V_RSTB": "PWL(0 0.00 0.99u 0.00 1.00u 3.30)",
 "V_RSTR": "PWL(0 0.00 11.49u 0.00 11.50u 3.30)",
 "V_PHIB": "PWL(0 3.30 0.99u 3.30 1.00u 0.00 10.99u 0.00 11.00u 3.30)",
 "V_PHI":  "PWL(0 0.00 0.99u 0.00 1.00u 3.30 10.99u 3.30 11.00u 0.00)"}
def railctl(t):
    for name, w in REPL.items():
        t, n = re.subn(rf"^({name}\s+\S+\s+0\s+)PWL\(.*\)\s*$", rf"\g<1>{w}", t, flags=re.M); assert n == 1, name
    return t
