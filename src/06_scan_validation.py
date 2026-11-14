"""
Step 6 - Checks of the spatial scan used in Paper 5.

1 Independent re-implementation: every window (a community centroid plus its nearest neighbours) is enumerated by
  brute force and its Bernoulli log-likelihood ratio (LLR) recomputed with separately written code; the most likely
  window and LLR must match 05_analysis.py exactly.
2 Calibration (type I error): 500 simulated data sets in which communities differ in participation (beta-binomial,
  intraclass correlation estimated from Round 3) but with NO spatial pattern. A well-calibrated test should give
  p < 0.05 in about 5% of them. Compared: (a) the community-permutation scan of this paper; (b) the standard
  Bernoulli scan (SaTScan-type null, cases relabelled among individuals).
3 Power: 300 data sets per scenario with a planted cluster of three neighbouring communities whose non-participation
  is raised by 15, 25 or 35 percentage points.
4 SaTScan input files (case, population and coordinate files per round) so the household-level scan can be re-run in
  the free SaTScan software. These contain coordinates and are written only to the (uncommitted) outputs folder.

Usage
    python -I 06_scan_validation.py <paper5_spatial.csv> <p5_results.pkl> <output_folder>
"""

import sys, json, pickle, os
import numpy as np, pandas as pd
from scipy.special import xlogy
import geopandas as gpd

SRC, PKL, OUT = sys.argv[1:4]
os.makedirs(OUT, exist_ok=True)
CODE = json.load(open(__import__("os").environ.get("COMMUNITY_KEY", "data/community_codes.json")))
d = pd.read_csv(SRC)
med = d[d.gps_lat.notna() & (d.gps_flag != 5)].groupby("community_name")[["gps_lon", "gps_lat"]].median()
cent = gpd.GeoDataFrame(med, geometry=gpd.points_from_xy(med.gps_lon, med.gps_lat), crs=4326).to_crs(32630)
cent["x"] = cent.geometry.x
cent["y"] = cent.geometry.y
R = pickle.load(open(PKL, "rb"))["rev"]["comm_scan"]


def comm_data(k):
    A = d[(d["round"] == k) & (d.recall_mda == 1)].dropna(subset=["received"])
    g = A.groupby("community_name").received.agg(n="size", s="sum").join(cent[["x", "y"]], how="inner")
    g["c"] = g.n - g.s
    return g


# ---------------------------------------------------------------- 1. independent brute-force LLR


# Bernoulli log-likelihood c log(p) + (n - c) log(1 - p) at the maximum-likelihood p = c/n; 0 log 0
# is taken as 0.
def loglik(c, n):  # Bernoulli log-likelihood at the MLE
    return xlogy(c, c / n) + xlogy(n - c, (n - c) / n) if n > 0 else 0.0


# Brute force: list every window explicitly and recompute its LLR = loglik(inside) + loglik(outside)
# - loglik(all), keeping only windows with higher risk inside.
def brute(g, maxfrac):
    N, C = g.n.sum(), g.c.sum()
    X = g[["x", "y"]].values
    names = list(g.index)
    L0 = loglik(C, N)
    best = (-1, None)
    for i in range(len(g)):
        dist = np.hypot(X[:, 0] - X[i, 0], X[:, 1] - X[i, 1])
        order = np.argsort(dist, kind="stable")
        for k in range(1, len(g) + 1):
            mem = order[:k]
            n_in = g.n.values[mem].sum()
            c_in = g.c.values[mem].sum()
            if n_in > maxfrac * N:
                break
            if c_in / n_in <= (C - c_in) / (N - n_in):
                continue
            llr = loglik(c_in, n_in) + loglik(C - c_in, N - n_in) - L0
            if llr > best[0]:
                best = (llr, sorted(CODE[names[m]] for m in mem))
    return best


check = []
for k in (1, 2, 3):
    g = comm_data(k)
    for mf in (0.10, 0.25, 0.50):
        llr, codes = brute(g, mf)
        orig = R[k][mf]["clusters"][0]
        check.append(
            dict(
                round=k,
                maxfrac=mf,
                llr_brute=llr,
                llr_main=float(orig["llr"]),
                codes_brute=", ".join(codes),
                codes_main=", ".join(sorted(orig["codes"])),
                N=int(g.n.sum()),
                C=int(g.c.sum()),
                match=bool(abs(llr - orig["llr"]) < 1e-8 and codes == sorted(orig["codes"])),
            )
        )
check = pd.DataFrame(check)
print(check.to_string())


# ---------------------------------------------------------------- 2–3. calibration and power


# Fast maximum LLR over all windows for one simulated data set (used in the simulations).
def max_llr(cv, nv, order, maxfrac):
    N, C = nv.sum(), cv.sum()
    best = 0.0
    cc = np.cumsum(cv[order], axis=1)
    nn = np.cumsum(nv[order], axis=1)
    ok = nn <= maxfrac * N
    cin = cc / nn
    cout = np.where(N - nn > 0, (C - cc) / np.maximum(N - nn, 1e-12), 0)
    L = (
        xlogy(cc, cin)
        + xlogy(nn - cc, 1 - cin)
        + xlogy(C - cc, cout)
        + xlogy(N - nn - C + cc, 1 - cout)
        - (xlogy(C, C / N) + xlogy(N - C, 1 - C / N))
    )
    L = np.where(ok & (cin > cout), L, 0.0)
    return L.max()


def p_perm(cv, nv, order, rg, nperm=199, mf=0.25):  # community permutation (this paper)
    obs = max_llr(cv, nv, order, mf)
    null = [max_llr(cv[p], nv[p], order, mf) for p in (rg.permutation(len(cv)) for _ in range(nperm))]
    return (np.sum(np.array(null) >= obs - 1e-12) + 1) / (nperm + 1)


def p_bern(cv, nv, order, rg, nperm=199, mf=0.25):  # standard Bernoulli: cases relabelled among individuals
    obs = max_llr(cv, nv, order, mf)
    C = int(cv.sum())
    null = [
        max_llr(rg.multivariate_hypergeometric(nv.astype(int), C).astype(float), nv, order, mf)
        for _ in range(nperm)
    ]
    return (np.sum(np.array(null) >= obs - 1e-12) + 1) / (nperm + 1)


g3 = comm_data(3)
nv = g3.n.values.astype(float)
X = g3[["x", "y"]].values
order = np.argsort(
    np.hypot(X[:, None, 0] - X[None, :, 0], X[:, None, 1] - X[None, :, 1]), axis=1, kind="stable"
)
p_hat = g3.c.sum() / g3.n.sum()
# between-community variance of non-participation (method of moments, beta-binomial intraclass correlation)
pi = g3.c / g3.n
nbar = g3.n.mean()
s2 = np.average((pi - p_hat) ** 2, weights=g3.n) * len(g3) / (len(g3) - 1)

# Intraclass correlation of non-participation in Round 3 by the method of moments; it sets how much
# community participation varies in the simulated data (beta-binomial).
rho = max(0.01, (s2 - p_hat * (1 - p_hat) / nbar) / (p_hat * (1 - p_hat) * (1 - 1 / nbar)))
rg = np.random.default_rng(20261105)
NS = 500


# Simulate non-participants per community: each community draws its own probability from a beta
# distribution with the observed mean and intraclass correlation, then a binomial count. Location
# plays no role, so any 'cluster' found is a false alarm.
def sim_counts(pvec):
    a = pvec * (1 - rho) / rho
    b = (1 - pvec) * (1 - rho) / rho
    return rg.binomial(nv.astype(int), rg.beta(a, b)).astype(float)


cal = {"perm": [], "bern": []}
for s in range(NS):
    cv = sim_counts(np.full(len(nv), p_hat))
    if cv.sum() == 0:
        continue
    cal["perm"].append(p_perm(cv, nv, order, rg))
    cal["bern"].append(p_bern(cv, nv, order, rg))
typeI = {k: float(np.mean(np.array(v) <= 0.05)) for k, v in cal.items()}
# power: three nearest neighbours of a central community at non-participation p_hat + delta; others p_hat
centre = int(np.argmin(np.hypot(X[:, 0] - X[:, 0].mean(), X[:, 1] - X[:, 1].mean())))
members = order[centre, :3]
power = {}
for delta in (0.15, 0.25, 0.35):
    pv = np.full(len(nv), p_hat)
    pv[members] = p_hat + delta
    res = {"perm": [], "bern": []}
    for s in range(300):
        cv = sim_counts(pv)
        res["perm"].append(p_perm(cv, nv, order, rg))
        res["bern"].append(p_bern(cv, nv, order, rg))
    power[delta] = {k: float(np.mean(np.array(v) <= 0.05)) for k, v in res.items()}
sim = dict(
    rho=float(rho),
    p_hat=float(p_hat),
    nsim=len(cal["perm"]),
    typeI=typeI,
    power=power,
    planted=[CODE[g3.index[m]] for m in members],
)
print(sim)

# ---------------------------------------------------------------- 4. SaTScan input files (codes only; projected metres -> Cartesian)
for k in (1, 2, 3):
    g = comm_data(k)
    g.index = [CODE[c] for c in g.index]
    g[["c"]].astype(int).to_csv(
        f"{OUT}/satscan_round{k}.cas", sep=" ", header=False
    )  # location, #cases (non-participants)
    (g.n - g.c).astype(int).to_frame().to_csv(
        f"{OUT}/satscan_round{k}.ctl", sep=" ", header=False
    )  # controls (participants)
    g[["x", "y"]].round(1).to_csv(
        f"{OUT}/satscan_round{k}.geo", sep=" ", header=False
    )  # Cartesian coordinates (UTM 30N metres)
pickle.dump(dict(check=check, sim=sim), open(f"{OUT}/scan_validation.pkl", "wb"))
print("saved")
