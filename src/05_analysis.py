"""Paper 5 – spatial patterns of black-fly exposure and treatment receipt.
Usage: python3 -I analysis.py <paper5_spatial.csv> <gisdir> <outdir>"""
import sys, os, pickle, warnings
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd, geopandas as gpd
from scipy import stats
import statsmodels.api as sm
from patsy import dmatrix, build_design_matrices
import libpysal
from esda.moran import Moran
from esda.getisord import G_Local
import core
from core import Fit, design, CAT, REF, standardise, cluster_prop
np.random.seed(20261103)  # global seed so permutation tests (esda) and multiple imputation are reproducible
warnings.filterwarnings('ignore')
rng = np.random.default_rng(20261104)
SRC, GIS, OUT = sys.argv[1:4]
R = {}

d = pd.read_csv(SRC)
TIER1 = ['age_grp', 'female', 'educ4', 'ses_q', 'farming_hh', 'permanent_res', 'wg_disability']

# ------------------------------------------------------------------ geometry & distances
tam = gpd.read_file(f'{GIS}/tam_district.gpkg')
hr = gpd.read_file(f'{GIS}/rivers_tam_region.gpkg')
osm = gpd.read_file(f'{GIS}/osm_waterways.gpkg') if os.path.exists(f'{GIS}/osm_waterways.gpkg') else None
sett = gpd.read_file(f'{GIS}/tam_communities_all.gpkg')
med = d[d.gps_lat.notna() & (d.gps_flag != 5)].groupby('community_name')[['gps_lon', 'gps_lat']].median()
d['has_gps'] = d.gps_lat.notna()
d['lon_imp'] = d.gps_lon.fillna(d.community_name.map(med.gps_lon))
d['lat_imp'] = d.gps_lat.fillna(d.community_name.map(med.gps_lat))
G = gpd.GeoDataFrame(d, geometry=gpd.points_from_xy(d.lon_imp, d.lat_imp), crs=4326).to_crs(32630)
d['x'], d['y'] = G.geometry.x.values, G.geometry.y.values
big = hr[hr.ORD_STRA >= 3].geometry.union_all(); hr_all = hr.geometry.union_all()
d['d_big'] = G.distance(big).values / 1000
d['d_hr'] = G.distance(hr_all).values / 1000
if osm is not None:
    d['d_osm'] = G.distance(osm.geometry.union_all()).values / 1000
    rv = osm[osm.waterway == 'river']
    d['d_osm_river'] = G.distance(rv.geometry.union_all()).values / 1000 if len(rv) else np.nan
R['osm_n'] = None if osm is None else osm.waterway.value_counts().to_dict()
R['hr_n'] = hr.ORD_STRA.value_counts().sort_index().to_dict()
cent = gpd.GeoDataFrame(med, geometry=gpd.points_from_xy(med.gps_lon, med.gps_lat), crs=4326).to_crs(32630)
cent['x'], cent['y'] = cent.geometry.x, cent.geometry.y
for c in ['d_big', 'd_hr', 'd_osm']:
    if c in d: cent[c] = d[d.has_gps].groupby('community_name')[c].median()
R['district_km2'] = tam.area.iloc[0] / 1e6; R['n_settlements'] = len(sett)

d['dq_big'] = pd.qcut(d.loc[d['round'] == 3, 'd_big'].rank(method='first'), 4, labels=[1, 2, 3, 4]).reindex(d.index).astype(float)
qcut_edges = d.loc[d['round'] == 3, 'd_big'].quantile([0, .25, .5, .75, 1]).values
def q_big(v): return np.digitize(v, qcut_edges[1:-1]) + 1
d['dq_big'] = q_big(d.d_big)
if 'd_osm' in d:
    e2 = d.loc[d['round'] == 3, 'd_osm'].quantile([0, .25, .5, .75, 1]).values
    d['dq_osm'] = np.digitize(d.d_osm, e2[1:-1]) + 1
    R['osm_edges'] = e2
R['big_edges'] = qcut_edges
for v, n in [('dq_big', 4), ('dq_osm', 4)]:
    CAT[v] = [1, 2, 3, 4]; REF[v] = 1
d['season_wet'] = (d.blackfly_season == 1).astype(float).where(d.blackfly_season.notna())
d['fly_time'] = d.blackfly_time; CAT['fly_time'] = [1, 2, 3, 4]; REF['fly_time'] = 1
d['river_dries_yes'] = d.river_dries.map({0: 0, 1: 1})
d['river_agri'] = (d.river_activity == 1).astype(float).where(d.river_activity.notna())
d['near_river_self'] = d.river_dist_grp; CAT['near_river_self'] = [1, 2, 3, 4]; REF['near_river_self'] = 1
d['log_d_big'] = np.log(d.d_big)

R3 = d[d['round'] == 3].copy()
A3 = R3[R3.recall_mda == 1].copy()                 # 362
A3g = A3[A3.has_gps].copy()                        # primary (complete GPS) 326
R['n'] = dict(R3=len(R3), A3=len(A3), A3g=len(A3g), R3g=int(R3.has_gps.sum()))

# ================================================================== OBJ 1: exposure description
def pct(s): s = s.dropna(); return 100 * s.mean() if len(s) else np.nan
t1 = []
for c, g in R3.groupby('community_name'):
    gg = g[g.has_gps]
    t1.append(dict(community=c, n=len(g), n_gps=len(gg), recalled=int(g.recall_mda.sum()),
                   flies=pct(g.blackflies_yes), flies_def=pct((g.blackflies == 5).astype(float).where(g.blackflies.notna() & (g.blackflies != 98))),
                   wet=pct(g.season_wet), fast=pct(g.fast_river), dries=pct(g.river_dries_yes), agri=pct(g.river_agri),
                   self_min=g.river_dist_min.median(), d_big=gg.d_big.median() if len(gg) else np.nan,
                   d_hr=gg.d_hr.median() if len(gg) else np.nan, d_osm=gg.d_osm.median() if ('d_osm' in gg and len(gg)) else np.nan,
                   receipt=pct(g.received)))
t1 = pd.DataFrame(t1).sort_values('d_big')
gg = R3[R3.has_gps]
tot = dict(community='All communities', n=len(R3), n_gps=len(gg), recalled=int(R3.recall_mda.sum()), flies=pct(R3.blackflies_yes),
           flies_def=pct((R3.blackflies == 5).astype(float).where(R3.blackflies.notna() & (R3.blackflies != 98))), wet=pct(R3.season_wet),
           fast=pct(R3.fast_river), dries=pct(R3.river_dries_yes), agri=pct(R3.river_agri), self_min=R3.river_dist_min.median(),
           d_big=gg.d_big.median(), d_hr=gg.d_hr.median(), d_osm=gg.d_osm.median() if 'd_osm' in gg else np.nan, receipt=pct(R3.received))
R['table1'] = pd.concat([t1, pd.DataFrame([tot])], ignore_index=True)
R['fly_time'] = R3.blackfly_time.value_counts(normalize=True).sort_index().to_dict()
R['fly_season'] = R3.blackfly_season.value_counts(normalize=True).sort_index().to_dict()

# agreement: self-reported minutes vs GIS distances
def spearman_ci(x, y, cl=None, B=2000):
    ok = ~(np.isnan(x) | np.isnan(y)); x, y = x[ok], y[ok]
    r = stats.spearmanr(x, y)[0]
    if cl is None:
        z = np.arctanh(r); se = 1.06 / np.sqrt(len(x) - 3); return r, np.tanh(z - 1.96 * se), np.tanh(z + 1.96 * se), len(x)
    cl = np.asarray(cl)[ok]; ug = np.unique(cl); bs = []
    for _ in range(B):
        pick = rng.choice(ug, len(ug)); idx = np.concatenate([np.where(cl == u)[0] for u in pick])
        bs.append(stats.spearmanr(x[idx], y[idx])[0])
    return r, np.nanpercentile(bs, 2.5), np.nanpercentile(bs, 97.5), len(x)
def wkappa(a, b):
    a = pd.qcut(pd.Series(a).rank(method='first'), 4, labels=False); b = pd.qcut(pd.Series(b).rank(method='first'), 4, labels=False)
    O = pd.crosstab(a, b).values.astype(float); n = O.sum(); k = O.shape[0]
    W = np.array([[(i - j) ** 2 for j in range(k)] for i in range(k)]) / (k - 1) ** 2
    E = np.outer(O.sum(1), O.sum(0)) / n
    return 1 - (W * O).sum() / (W * E).sum()
ag = []
x = R3[R3.has_gps & R3.river_dist_min.notna()]
for v, lab in [('d_big', 'Larger river (Strahler order ≥3, HydroRIVERS)'), ('d_hr', 'Any river (HydroRIVERS)'),
               ('d_osm', 'Any waterway (OpenStreetMap)'), ('d_osm_river', 'River (OpenStreetMap waterway=river)')]:
    if v not in x or x[v].isna().all(): continue
    r = spearman_ci(x.river_dist_min.values, x[v].values, x.community_name.values)
    cm = x.groupby('community_name')[['river_dist_min', v]].median()
    rc = stats.spearmanr(cm.river_dist_min, cm[v])
    ag.append(dict(measure=lab, var=v, median_km=x[v].median(), iqr=(x[v].quantile(.25), x[v].quantile(.75)),
                   rho=r[0], lo=r[1], hi=r[2], n=r[3], kappa=wkappa(x.river_dist_min.values, x[v].values),
                   rho_comm=rc[0], p_comm=rc[1], n_comm=len(cm)))
R['agreement'] = pd.DataFrame(ag); R['self_minutes'] = (x.river_dist_min.median(), x.river_dist_min.quantile(.25), x.river_dist_min.quantile(.75))

# perceived black flies vs objective distance (R3, all respondents with GPS)
pf = []
for v in ['dq_big', 'dq_osm']:
    if v not in d: continue
    f = Fit(R3[R3.has_gps], [v] + TIER1, y='blackflies_yes')
    tb = f.ratio_table(); tb = tb[tb.term.str.startswith(v)]
    lv = R3[R3.has_gps].groupby(v).blackflies_yes.agg(['sum', 'count'])
    pf.append(dict(var=v, table=tb, levels=lv, wald=f.wald([c for c in f.X.columns if c.startswith(v)]), n=f.n))
R['flies_vs_distance'] = pf

# ================================================================== OBJ 2: clustering of non-receipt
def eb_smooth(x, n):
    p = x / n; m = x.sum() / n.sum(); v = np.sum(n * (p - m) ** 2) / n.sum() - m * (1 - m) / n.mean()
    v = max(v, 1e-6); a = m * (m * (1 - m) / v - 1); b = (1 - m) * (m * (1 - m) / v - 1)
    return (x + a) / (n + a + b)
def moran_comm(df, k=4, idw=False):
    g = df.groupby('community_name').received.agg(['sum', 'count']).join(cent[['x', 'y']], how='inner')
    g['eb'] = eb_smooth(g['sum'].values, g['count'].values)
    pts = g[['x', 'y']].values
    if idw:
        w = libpysal.weights.DistanceBand(pts, threshold=1e9, binary=False, alpha=-1.0, silence_warnings=True)
    else:
        w = libpysal.weights.KNN(pts, k=k)
    w.transform = 'r'
    m = Moran(g.eb.values, w, permutations=999)
    gl = G_Local(g.eb.values, w, star=True, permutations=999, transform='R')
    g['gi_z'] = gl.Zs; g['gi_p'] = gl.p_sim
    return m, g
mor = {}
for k_ in (1, 2, 3):
    A = d[(d['round'] == k_) & (d.recall_mda == 1)]
    res = {}
    for spec, kw in [('knn4', dict(k=4)), ('knn3', dict(k=3)), ('knn5', dict(k=5)), ('idw', dict(idw=True))]:
        m, g = moran_comm(A, **kw); res[spec] = dict(I=m.I, EI=m.EI, z=m.z_sim, p=m.p_sim)
        if spec == 'knn4': res['gi'] = g
    mor[k_] = res
R['moran'] = mor

# Kulldorff Bernoulli spatial scan (cases = non-recipients), centres = public settlement points
scx = sett.geometry.x.values; scy = sett.geometry.y.values
def scan(df, maxfrac=0.25, nsim=999):
    df = df.dropna(subset=['received'])
    px, py = df.x.values, df.y.values; yv = (df.received == 0).astype(int).values
    N, C = len(yv), yv.sum(); kmax = int(np.floor(maxfrac * N))
    D = np.sqrt((scx[:, None] - px[None, :]) ** 2 + (scy[:, None] - py[None, :]) ** 2)
    order = np.argsort(D, axis=1)[:, :kmax]; radii = np.take_along_axis(D, order, axis=1)
    nn = np.arange(1, kmax + 1)[None, :]
    def llr_all(yy):
        c = np.cumsum(yy[order], axis=1).astype(float)
        cin = c / nn; cout = (C - c) / (N - nn)
        with np.errstate(divide='ignore', invalid='ignore'):
            def xl(a, b): return np.where(a > 0, a * np.log(b), 0.0)
            ll = xl(c, cin) + xl(nn - c, 1 - cin) + xl(C - c, cout) + xl(N - nn - C + c, 1 - cout)
        l0 = xl(np.array(C, float), C / N) + xl(np.array(N - C, float), 1 - C / N)
        L = ll - l0; L[cin <= cout] = 0; L = np.nan_to_num(L)
        # windows only at distinct radii (ties) – use last index of each radius
        return L
    L = llr_all(yv)
    null = np.array([llr_all(rng.permutation(yv)).max() for _ in range(nsim)])
    # greedy non-overlapping clusters
    clusters = []; used = np.zeros(N, bool); Lw = L.copy()
    for _ in range(5):
        i, j = np.unravel_index(np.argmax(Lw), Lw.shape)
        if Lw[i, j] <= 0: break
        members = order[i, :j + 1]
        if used[members].any():
            Lw[i, j] = 0; continue
        p = (np.sum(null >= L[i, j]) + 1) / (nsim + 1)
        c = yv[members].sum(); n_ = j + 1
        clusters.append(dict(centre=sett.iloc[i].Community, radius_km=radii[i, j] / 1000, n=n_, obs=int(c), exp=C * n_ / N,
                             rr=(c / n_) / ((C - c) / (N - n_)), llr=L[i, j], p=p,
                             communities=sorted(df.iloc[members].community_name.unique()),
                             cx=scx[i], cy=scy[i], r=radii[i, j]))
        used[members] = True
        # remove all windows overlapping used points
        ov = used[order].any(axis=1)
        Lw[ov, :] = np.where(np.cumsum(used[order], axis=1)[ov] > 0, 0, Lw[ov, :])
        if len(clusters) >= 3: break
    return dict(N=N, C=int(C), clusters=clusters)
scans = {}
for k_ in (1, 2, 3):
    A = d[(d['round'] == k_) & (d.recall_mda == 1) & d.has_gps]
    scans[k_] = scan(A)
R['scan'] = scans
A_imp3 = d[(d['round'] == 3) & (d.recall_mda == 1)]
R['scan_r3_imputed'] = scan(A_imp3)

# persistence
comm_rec = d[d.recall_mda == 1].groupby(['community_name', 'round']).received.mean().unstack()
pers = {}
for a, b in [(1, 2), (2, 3), (1, 3)]:
    s = comm_rec[[a, b]].dropna(); r = stats.spearmanr(s[a], s[b]); pers[f'R{a}-R{b}'] = (r[0], r[1], len(s))
R['persistence'] = pers; R['comm_round'] = comm_rec

# ================================================================== OBJ 3: exposure–receipt (R3)
EXPO = [('dq_big', 'Distance to larger river (quartile)'), ('dq_osm', 'Distance to any OpenStreetMap waterway (quartile)'),
        ('blackflies_yes', 'Black flies perceived present'), ('season_wet', 'Black flies mainly in wet season'),
        ('fly_time', 'Time of day black flies noticed'), ('fast_river', 'Fast-flowing river nearby'),
        ('river_dries_yes', 'River dries in dry season'), ('river_agri', 'Farming is main river activity'),
        ('near_river_self', 'Self-reported round-trip time to river')]
CAT['near_river_self'] = [1, 2, 3, 4]
m1 = []
for v, lab in EXPO:
    if v not in d: continue
    df_ = A3g.dropna(subset=[v])
    if df_[v].nunique() < 2: continue
    f = Fit(df_, [v] + TIER1)
    tb = f.ratio_table(); tb = tb[tb.term.str.startswith(v)]
    fu = Fit(df_, [v]); tu = fu.ratio_table(); tu = tu[tu.term.str.startswith(v)]
    lv = df_.groupby(v).received.agg(['sum', 'count'])
    W = f.wald([c for c in f.X.columns if c.startswith(v)])
    m1.append(dict(var=v, label=lab, adj=tb, unadj=tu, levels=lv, wald=W, n=f.n, G=f.G))
R['model1'] = m1

# Model 2: spline of distance to larger river + perceived flies
A3g['ld'] = np.log(A3g.d_big)
sp = dmatrix('cr(ld, df=3, constraints="center") - 1', A3g, return_type='dataframe'); sp_info = sp.design_info
sp.columns = ['sp1', 'sp2', 'sp3']
A3s = pd.concat([A3g, sp], axis=1)
f2 = Fit(A3s, ['sp1', 'sp2', 'sp3', 'blackflies_yes'] + TIER1)
grid = np.exp(np.linspace(np.log(0.1), np.log(10), 60))
Sg = build_design_matrices([sp_info], {'ld': np.log(grid)})[0]
curve = []
pop = f2.df.copy()
def curve_at(b):
    out = []
    for i in range(len(grid)):
        p2 = pop.copy(); p2[['sp1', 'sp2', 'sp3']] = np.asarray(Sg)[i]
        out.append(f2.predict(p2, b).mean())
    return np.array(out)
c0 = curve_at(f2.b); eps = 1e-6; J = np.zeros((len(grid), len(f2.b)))
for j in range(len(f2.b)):
    bb = f2.b.copy(); bb[j] += eps; J[:, j] = (curve_at(bb) - c0) / eps
se = np.sqrt(np.einsum('ij,jk,ik->i', J, f2.V, J))
R['curve'] = pd.DataFrame(dict(km=grid, est=c0, lo=c0 - f2.tcrit * se, hi=c0 + f2.tcrit * se))
R['model2_spline_wald'] = f2.wald(['sp1', 'sp2', 'sp3'])
tb2 = f2.ratio_table(); R['model2_flies'] = tb2[tb2.term == 'blackflies_yes'].iloc[0].to_dict(); R['model2_n'] = f2.n
# residual Moran (household, kNN 8)
resid = (f2.df.received - f2.m.mu) / np.sqrt(f2.m.mu)
wk = libpysal.weights.KNN(f2.df[['x', 'y']].values + rng.normal(0, 1, (len(f2.df), 2)), k=8); wk.transform = 'r'
mr = Moran(resid.values, wk, permutations=999)
R['resid_moran'] = dict(I=mr.I, p=mr.p_sim)
# raw household Moran for comparison (Model with Tier1 only)
f0 = Fit(A3g, TIER1); r0 = (f0.df.received - f0.m.mu) / np.sqrt(f0.m.mu)
wk0 = libpysal.weights.KNN(f0.df[['x', 'y']].values + rng.normal(0, 1, (len(f0.df), 2)), k=8); wk0.transform = 'r'
m0 = Moran(r0.values, wk0, permutations=999); R['resid_moran_tier1'] = dict(I=m0.I, p=m0.p_sim)

# ================================================================== OBJ 4: exposure–receipt alignment (R3 communities)
g = A3.groupby('community_name').received.agg(['sum', 'count'])
g['p'] = g['sum'] / g['count']
g['lo'] = [stats.beta.ppf(.025, x, n - x + 1) if x > 0 else 0 for x, n in zip(g['sum'], g['count'])]
g['hi'] = [stats.beta.ppf(.975, x + 1, n - x) if x < n else 1 for x, n in zip(g['sum'], g['count'])]
g['eb'] = eb_smooth(g['sum'].values, g['count'].values)
g['flies'] = R3.groupby('community_name').blackflies_yes.mean()
g['d_big'] = cent.d_big.reindex(g.index)
z = lambda s: (s - s.mean()) / s.std()
g['expo'] = (z(g.flies) + z(-np.log(g.d_big))) / 2
mx, my = g.expo.median(), g.eb.median()
g['quad'] = np.select([(g.expo >= mx) & (g.eb < my), (g.expo >= mx) & (g.eb >= my), (g.expo < mx) & (g.eb < my)],
                      ['High exposure, low receipt', 'High exposure, high receipt', 'Low exposure, low receipt'], 'Low exposure, high receipt')
nr = A3[A3.received == 0]
g['main_reason'] = nr.groupby('community_name').reason_not_received.agg(lambda s: s.value_counts().index[0] if len(s.dropna()) else np.nan)
g['n_nonrec'] = nr.groupby('community_name').size()
g['reasons'] = nr.groupby('community_name').reason_not_received.agg(lambda s: s.value_counts().to_dict())
g = g.fillna({'n_nonrec': 0})
R['quadrant'] = g; R['quad_cut'] = (mx, my)
R['expo_receipt_corr'] = stats.spearmanr(g.expo, g.eb)

# ================================================================== OBJ 5: exploratory
ex = []
for yv, frame, lab in [('know_flies', R3[R3.has_gps], 'Knows black flies transmit onchocerciasis'),
                       ('ae_any', A3g[A3g.received == 1], 'Any self-reported side effect (recipients)')]:
    for v in ['dq_big', 'blackflies_yes']:
        df_ = frame.dropna(subset=[yv, v])
        f = Fit(df_, [v] + TIER1, y=yv)
        tb = f.ratio_table(); tb = tb[tb.term.str.startswith(v)]
        ex.append(dict(outcome=lab, y=yv, var=v, table=tb, levels=df_.groupby(v)[yv].agg(['sum', 'count']),
                       wald=f.wald([c for c in f.X.columns if c.startswith(v)]), n=f.n))
R['explore'] = ex

# ================================================================== SENSITIVITY (exposure–receipt, R3)
def key_estimates(frame, dvar='dq_big', y='received'):
    out = {}
    f = Fit(frame.dropna(subset=[dvar]), [dvar] + TIER1, y=y); tb = f.ratio_table().set_index('term')
    out['q4'] = tuple(tb.loc[f'{dvar}=4', ['est', 'lo', 'hi']]) if f'{dvar}=4' in tb.index else (np.nan,) * 3
    out['q_wald'] = f.wald([c for c in f.X.columns if c.startswith(dvar)])[2]
    f = Fit(frame.dropna(subset=['blackflies_yes']), ['blackflies_yes'] + TIER1, y=y); tb = f.ratio_table().set_index('term')
    out['flies'] = tuple(tb.loc['blackflies_yes', ['est', 'lo', 'hi']]); out['n'] = f.n
    return out
S = {}
S['main'] = key_estimates(A3g)
S['imputed'] = key_estimates(A3)
S['no_flagged'] = key_estimates(A3g[A3g.gps_flag != 5])
if 'dq_osm' in d: S['osm'] = key_estimates(A3g, 'dq_osm')
R3all = R3.copy(); R3all['received_upper'] = R3all.received.where(R3all.recall_mda == 1, 1.0)
S['lower'] = key_estimates(R3all[R3all.has_gps], y='received_itt')
S['upper'] = key_estimates(R3all[R3all.has_gps], y='received_upper')
# all rounds: perceived flies with round
CAT['round'] = [1, 2, 3]; REF['round'] = 1
Aall = d[(d.recall_mda == 1)]
f = Fit(Aall.dropna(subset=['blackflies_yes']), ['round', 'blackflies_yes'] + TIER1); tb = f.ratio_table().set_index('term')
S['allrounds_flies'] = (tuple(tb.loc['blackflies_yes', ['est', 'lo', 'hi']]), f.n)
R['sens'] = S


# ================================================================== REVISION (peer review)
REV = {}
CODE = __import__('json').load(open(__import__('os').environ.get('COMMUNITY_KEY', 'data/community_codes.json')))
# --- community-level scan: units = surveyed communities; windows = k nearest communities around each community centroid;
#     null = random permutation of community (cases, n) pairs across locations (tests spatial arrangement beyond community heterogeneity)
def comm_scan(df, maxfrac=0.25, nsim=999, seed=11):
    rg = np.random.default_rng(seed)
    g = df.dropna(subset=['received']).groupby('community_name').received.agg(n='size', s='sum').join(cent[['x', 'y']], how='inner')
    g['c'] = g.n - g.s; N, C = g.n.sum(), g.c.sum()
    X = g[['x', 'y']].values; D = np.sqrt(((X[:, None, :] - X[None, :, :]) ** 2).sum(-1)); order = np.argsort(D, axis=1)
    def llr(cv, nv):
        best = []
        for i in range(len(g)):
            cc = np.cumsum(cv[order[i]]); nn = np.cumsum(nv[order[i]])
            ok = nn <= maxfrac * N
            cin = cc / nn; cout = (C - cc) / (N - nn)
            with np.errstate(divide='ignore', invalid='ignore'):
                xl = lambda a, b: np.where(a > 0, a * np.log(np.where(b > 0, b, 1)), 0.0)
                L = xl(cc, cin) + xl(nn - cc, 1 - cin) + xl(C - cc, cout) + xl(N - nn - C + cc, 1 - cout) - (xl(np.array(C, float), C / N) + xl(np.array(N - C, float), 1 - C / N))
            L = np.where(ok & (cin > cout), np.nan_to_num(L), 0.0); best.append(L)
        return np.array(best)
    cv, nv = g.c.values.astype(float), g.n.values.astype(float)
    L = llr(cv, nv)
    null = []
    for _ in range(nsim):
        perm = rg.permutation(len(g)); null.append(llr(cv[perm], nv[perm]).max())
    null = np.array(null); clusters = []; used = np.zeros(len(g), bool); Lw = L.copy()
    while len(clusters) < 3:
        i, j = np.unravel_index(np.argmax(Lw), Lw.shape)
        if Lw[i, j] <= 0: break
        mem = order[i, :j + 1]
        if used[mem].any(): Lw[i, j] = 0; continue
        p = (np.sum(null >= L[i, j]) + 1) / (nsim + 1)
        c = cv[mem].sum(); n_ = nv[mem].sum()
        clusters.append(dict(communities=[g.index[m] for m in mem], codes=[CODE[g.index[m]] for m in mem], n=int(n_), obs=int(c), exp=C * n_ / N,
                             rr=(c / n_) / ((C - c) / (N - n_)), llr=L[i, j], p=p, cx=X[i, 0], cy=X[i, 1], r=D[i, mem].max()))
        used[mem] = True; Lw[:, :] = np.where(np.array([[used[order[a, :b + 1]].any() for b in range(len(g))] for a in range(len(g))]), 0, Lw)
    return dict(N=int(N), C=int(C), G=len(g), clusters=clusters, seed=seed, nsim=nsim)
cs = {}
for k_ in (1, 2, 3):
    A_ = d[(d['round'] == k_) & (d.recall_mda == 1)]
    cs[k_] = {mf: comm_scan(A_, mf) for mf in (0.10, 0.25, 0.50)}
REV['comm_scan'] = cs
# --- Moran's I two-sided p, raw and EB, knn4; also Gi* significant communities
mor2 = {}
for k_ in (1, 2, 3):
    A_ = d[(d['round'] == k_) & (d.recall_mda == 1)]
    gq = A_.groupby('community_name').received.agg(['sum', 'count']).join(cent[['x', 'y']], how='inner')
    gq['raw'] = gq['sum'] / gq['count']; gq['eb'] = eb_smooth(gq['sum'].values, gq['count'].values)
    out = {}
    for spec, kw in [('knn3', dict(k=3)), ('knn4', dict(k=4)), ('knn5', dict(k=5)), ('idw', None)]:
        pts = gq[['x', 'y']].values
        w = libpysal.weights.DistanceBand(pts, threshold=1e9, binary=False, alpha=-1.0, silence_warnings=True) if kw is None else libpysal.weights.KNN(pts, **kw)
        w.transform = 'r'
        for val in ('eb', 'raw'):
            m = Moran(gq[val].values, w, permutations=9999)
            sims = m.sim; p2 = (np.sum(np.abs(sims - sims.mean()) >= abs(m.I - sims.mean())) + 1) / (len(sims) + 1)
            out[(spec, val)] = dict(I=m.I, EI=m.EI, p2=p2)
        if spec == 'knn4':
            gl = G_Local(gq['eb'].values, w, star=True, permutations=9999, transform='R')
            out['gi'] = pd.DataFrame(dict(code=[CODE[c] for c in gq.index], z=gl.Zs, p=gl.p_sim * 2), index=gq.index)
            nb = {CODE[gq.index[i]]: max(np.sqrt(((pts[i] - pts[j]) ** 2).sum()) for j in w.neighbors[i]) / 1000 for i in range(len(gq))}
            out['knn4_max_km'] = max(nb.values())
    out['G'] = len(gq); mor2[k_] = out
REV['moran2'] = mor2
# --- persistence with Fisher CIs (raw proportions, communities with n>=5)
cr_ = d[d.recall_mda == 1].groupby(['community_name', 'round']).received.agg(['mean', 'size']).reset_index()
cr_ = cr_[cr_['size'] >= 5].pivot(index='community_name', columns='round', values='mean')
pers2 = {}
for a, b in [(1, 2), (2, 3), (1, 3)]:
    s_ = cr_[[a, b]].dropna(); r = stats.spearmanr(s_[a], s_[b])[0]; n_ = len(s_); zz = np.arctanh(r); se_ = 1.06 / np.sqrt(n_ - 3)
    pers2[f'R{a}-R{b}'] = (r, np.tanh(zz - 1.96 * se_), np.tanh(zz + 1.96 * se_), stats.spearmanr(s_[a], s_[b])[1], n_)
REV['persistence'] = pers2; REV['comm_round'] = cr_
# --- persistent low participation (n>=5): below 80% in >=2 rounds; descriptors from Round 3
low = (cr_ < 0.8).sum(axis=1); nr_ = cr_.notna().sum(axis=1)
pl = pd.DataFrame(dict(rounds=nr_, low=low))
R3c = R3.groupby('community_name').agg(flies=('blackflies_yes', 'mean'), nonperm=('permanent_res', lambda s: 1 - s.mean()), n=('resp_uid', 'size'))
R3c['d_big'] = R3[R3.has_gps].groupby('community_name').d_big.median()
R3c['gps_n'] = R3[R3.has_gps].groupby('community_name').size()
pl = pl.join(cr_).join(R3c)
pl['code'] = [CODE[c] for c in pl.index]
pl['status'] = np.select([(pl.low == 3), pl.low >= 2], ['Below 80% in all three rounds', 'Below 80% in two rounds'], np.where(pl.rounds < 3, 'Not sampled in all rounds', 'Below 80% in at most one round'))
pl.loc[(pl.rounds < 3) & (pl.low >= 2), 'status'] = 'Below 80% in two rounds'
nr3 = A3[A3.received == 0]
pl['reasons'] = nr3.groupby('community_name').reason_not_received.agg(lambda s: s.value_counts().to_dict())
REV['persistent'] = pl
# --- exposure models with reduced adjustment set (≈5 parameters), unadjusted, and counts
A3g['age3'] = pd.cut(A3g.age, [13, 24, 44, 200], labels=[1, 2, 3]).astype(float)
A3g['ses_c'] = A3g.ses_index
CAT['age3'] = [1, 2, 3]; REF['age3'] = 1
RED = ['age3', 'female', 'permanent_res', 'ses_c']
m1r = []
for v, lab in EXPO:
    if v not in A3g: continue
    df_ = A3g.dropna(subset=[v] + RED)
    if df_[v].nunique() < 2: continue
    f = Fit(df_, [v] + RED); tb = f.ratio_table(); tb = tb[tb.term.str.startswith(v)]
    fu = Fit(df_, [v]); tu = fu.ratio_table(); tu = tu[tu.term.str.startswith(v)]
    lv = df_.groupby(v).received.agg(['sum', 'count']); lv['nonpart'] = lv['count'] - lv['sum']
    W = f.wald([c for c in f.X.columns if c.startswith(v)])
    m1r.append(dict(var=v, label=lab, adj=tb, unadj=tu, levels=lv, wald=W, n=f.n, k=f.X.shape[1], events=f.events))
REV['model1'] = m1r
# GEE exchangeable logistic for distance quartile and flies (sensitivity, accounts for within-community correlation)
gee = {}
for v in ['dq_big', 'blackflies_yes']:
    df_ = A3g.dropna(subset=[v] + RED)
    X = design(df_, [v] + RED); X = X.loc[:, X.std() > 0]; X['const'] = 1.0
    mg = sm.GEE(df_.received.astype(float), X, groups=df_.community_name, family=sm.families.Binomial(), cov_struct=sm.cov_struct.Exchangeable()).fit()
    ci_ = mg.conf_int(); gee[v] = pd.DataFrame(dict(OR=np.exp(mg.params), lo=np.exp(ci_[0]), hi=np.exp(ci_[1]), p=mg.pvalues)).loc[[c for c in X.columns if c.startswith(v)]]
REV['gee'] = gee
# community-level (ecological) association: R3 community participation vs median distance and % flies
cc3 = A3.groupby('community_name').received.mean().to_frame('p').join(R3c)
def sp_ci(a, b):
    r = stats.spearmanr(a, b); n_ = len(a); zz = np.arctanh(r[0]); se_ = 1.06 / np.sqrt(n_ - 3)
    return (r[0], np.tanh(zz - 1.96 * se_), np.tanh(zz + 1.96 * se_), r[1], n_)
REV['eco'] = dict(dist=sp_ci(cc3.p, cc3.d_big), flies=sp_ci(cc3.p, cc3.flies))
# --- spline restricted to 5th–95th percentile of household distances
q05, q95 = A3g.d_big.quantile(0.05), A3g.d_big.quantile(0.95)
cv_ = R['curve']; REV['curve_range'] = (q05, q95)
REV['curve'] = cv_[(cv_.km >= q05) & (cv_.km <= q95)].copy()
REV['hh_dist'] = A3g.d_big.values
# --- residual autocorrelation at community level (mean Pearson residual per community, knn4)
gr = pd.DataFrame(dict(res=resid.values, c=f2.df.community_name.values)).groupby('c').res.mean().to_frame().join(cent[['x', 'y']])
wq = libpysal.weights.KNN(gr[['x', 'y']].values, k=4); wq.transform = 'r'
mq = Moran(gr.res.values, wq, permutations=9999); sims = mq.sim
REV['resid_moran_comm'] = dict(I=mq.I, p2=(np.sum(np.abs(sims - sims.mean()) >= abs(mq.I - sims.mean())) + 1) / (len(sims) + 1), G=len(gr))
# --- misc reporting
REV['gps_by_round'] = {k_: (int(d[(d['round'] == k_) & d.has_gps].shape[0]), int((d['round'] == k_).sum())) for k_ in (1, 2, 3)}
REV['recall_n_by_round'] = {k_: int(d[(d['round'] == k_) & (d.recall_mda == 1) & d.has_gps].shape[0]) for k_ in (1, 2, 3)}
REV['n325_reason'] = int(A3g.blackflies_yes.isna().sum())
REV['flagged_in_A3g'] = int((A3g.gps_flag == 5).sum()) if 'gps_flag' in A3g else None
REV['gps_flag_by_round'] = d.groupby('round').gps_flag.value_counts().unstack(fill_value=0).to_dict() if 'gps_flag' in d else None
osm_ = gpd.read_file(f'{GIS}/osm_waterways.gpkg') if os.path.exists(f'{GIS}/osm_waterways.gpkg') else None
tam_ = gpd.read_file(f'{GIS}/tam_district.gpkg').to_crs(32630)
if osm_ is not None:
    REV['osm_len_km'] = float(gpd.clip(osm_.to_crs(32630), tam_).length.sum() / 1000)
hr_ = gpd.read_file(f'{GIS}/rivers_tam_region.gpkg').to_crs(32630); REV['hr_len_km'] = float(gpd.clip(hr_, tam_).length.sum() / 1000)
REV['river_dries_n'] = (int(A3g.river_dries_yes.notna().sum()), int(R3.river_dries_yes.notna().sum())) if 'river_dries_yes' in A3g else None
# --- sensitivity analyses re-run with the reduced adjustment set
def add_red(fr):
    fr = fr.copy(); fr['age3'] = pd.cut(fr.age, [13, 24, 44, 200], labels=[1, 2, 3]).astype(float); fr['ses_c'] = fr.ses_index; return fr
def key_red(frame, dvar='dq_big', y='received', extra=()):
    out = {}; fr = add_red(frame)
    a = fr.dropna(subset=[dvar, y] + RED); f = Fit(a, list(extra) + [dvar] + RED, y=y); tb = f.ratio_table().set_index('term')
    out['q4'] = tuple(tb.loc[f'{dvar}=4', ['est', 'lo', 'hi']]); out['q_wald'] = f.wald([c for c in f.X.columns if c.startswith(dvar)])[2]; out['n_d'] = f.n
    b = fr.dropna(subset=['blackflies_yes', y] + RED); f = Fit(b, list(extra) + ['blackflies_yes'] + RED, y=y); tb = f.ratio_table().set_index('term')
    out['flies'] = tuple(tb.loc['blackflies_yes', ['est', 'lo', 'hi']]); out['n'] = f.n
    return out
S2 = {'main': key_red(A3g), 'imputed': key_red(A3), 'no_flagged': key_red(A3g[A3g.gps_flag != 5])}
if 'dq_osm' in d: S2['osm'] = key_red(A3g, 'dq_osm')
S2['lower'] = key_red(R3all[R3all.has_gps], y='received_itt'); S2['upper'] = key_red(R3all[R3all.has_gps], y='received_upper')
fa = add_red(Aall).dropna(subset=['blackflies_yes'] + RED); f = Fit(fa, ['round', 'blackflies_yes'] + RED); tb = f.ratio_table().set_index('term')
S2['allrounds_flies'] = (tuple(tb.loc['blackflies_yes', ['est', 'lo', 'hi']]), f.n)
REV['sens'] = S2
print('S2', S2)
R['rev'] = REV
print('REV scan', {k: {mf: [(c['codes'], c['obs'], c['n'], round(c['rr'], 2), c['p']) for c in v[mf]['clusters']] for mf in v} for k, v in cs.items()})
print('moran2', {k: {kk: vv for kk, vv in v.items() if kk != 'gi'} for k, v in mor2.items()})
print('gi sig', {k: v['gi'][v['gi'].p < 0.05].to_dict('records') for k, v in mor2.items()})
print('pers', pers2); print(pl[['code', 'status', 1, 2, 3, 'flies', 'd_big', 'nonperm', 'gps_n']])
for m in m1r: print(m['var'], m['n'], m['k'], m['events'], m['adj'].round(3).to_dict('records'), m['levels'].to_dict())
print('gee', {k: v.round(3).to_dict('records') for k, v in gee.items()}); print('eco', REV['eco'], 'resid', REV['resid_moran_comm'], REV['curve_range'], REV.get('osm_len_km'), REV['hr_len_km'], REV['gps_by_round'], REV['n325_reason'], REV['flagged_in_A3g'], REV['river_dries_n'])

pickle.dump(R, open(f'{OUT}/p5_results.pkl', 'wb'))
print('n', R['n'])
print(R['agreement'][['measure', 'median_km', 'rho', 'lo', 'hi', 'kappa', 'rho_comm', 'p_comm']].round(3).to_string())
for k_ in (1, 2, 3): print('Moran', k_, {s: tuple(round(v, 3) for v in r.values()) for s, r in mor[k_].items() if s != 'gi'})
for k_ in (1, 2, 3): print('scan', k_, scans[k_]['C'], scans[k_]['N'], [(c['centre'], round(c['radius_km'], 1), c['n'], c['obs'], round(c['rr'], 2), round(c['p'], 3), c['communities']) for c in scans[k_]['clusters']])
print('persist', R['persistence'])
for m in m1: print(m['var'], m['n'], 'wald p', round(m['wald'][2], 3)); print(m['adj'].round(3).to_string()); print(m['levels'].to_string())
print('spline wald', R['model2_spline_wald'], 'flies', R['model2_flies'], 'resid Moran', R['resid_moran'], R['resid_moran_tier1'])
print(R['curve'].iloc[::10].round(3).to_string())
print(g[['sum', 'count', 'p', 'eb', 'flies', 'd_big', 'expo', 'quad', 'main_reason']].round(2).sort_values('expo').to_string())
print('expo-eb corr', R['expo_receipt_corr'])
for e in ex: print(e['outcome'], e['var'], round(e['wald'][2], 3)); print(e['table'].round(3).to_string())
for p_ in pf: print(p_['var'], round(p_['wald'][2], 4)); print(p_['table'].round(3).to_string()); print(p_['levels'].to_string())
print('SENS', {k: v for k, v in S.items()})
