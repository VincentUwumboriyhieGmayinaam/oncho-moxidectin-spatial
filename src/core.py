"""Shared modelling core (from Paper 3): design matrices, CR2 variance, modified Poisson fits, standardisation."""
import numpy as np, pandas as pd
from scipy import stats
import statsmodels.api as sm
CAT = {'round': [1, 2, 3], 'age_grp': [1, 2, 3, 4, 5, 6], 'educ4': [0, 1, 2, 3], 'ses_q': [1, 2, 3, 4, 5],
       'subdistrict': [1, 2, 3, 4, 5], 'river_dist_grp': [1, 2, 3, 4], 'interviewer': [1, 2, 3, 4, 5, 6]}
REF = {'round': 1, 'age_grp': 1, 'educ4': 0, 'ses_q': 1, 'subdistrict': 1, 'river_dist_grp': 1, 'interviewer': 1}
TIER1 = ['age_grp', 'female', 'educ4', 'ses_q', 'farming_hh', 'permanent_res', 'months_lt12', 'wg_disability']
TIER3 = ['info_radio', 'info_healthworker', 'info_cdd', 'info_cic', 'knowledge_score', 'concern_yes', 'blackflies_yes']
MODEL_A = ['round']
MODEL_B = ['round'] + TIER1 + ['subdistrict']
MODEL_C = MODEL_B + ['river_dist_grp'] + TIER3

def design(df, terms, interact=None):
    cols = {}
    for t in terms:
        if t in CAT:
            for lv in CAT[t]:
                if lv == REF.get(t, CAT[t][0]): continue
                cols[f'{t}={lv}'] = (df[t] == lv).astype(float)
        else:
            cols[t] = df[t].astype(float)
    if interact:
        a, b = interact
        for la in CAT['round'][1:]:
            for lb in (CAT[b][1:] if b in CAT else [None]):
                if lb is None:
                    cols[f'round={la}:{b}'] = (df['round'] == la) * df[b].astype(float)
                else:
                    cols[f'round={la}:{b}={lb}'] = ((df['round'] == la) & (df[b] == lb)).astype(float)
    X = pd.DataFrame(cols, index=df.index)
    X.insert(0, 'const', 1.0)
    return X

def cr2_vcov(X, y, mu, clusters, family='poisson', w=None):
    """CR2 (Bell–McCaffrey) cluster-robust covariance for a GLM with canonical link."""
    X = np.asarray(X); y = np.asarray(y); mu = np.asarray(mu)
    w = np.ones(len(y)) if w is None else np.asarray(w)
    if family == 'poisson': vf = mu
    elif family == 'binomial': vf = mu * (1 - mu)
    else: vf = np.ones_like(mu)                         # gaussian identity
    Wd = w * vf
    bread = np.linalg.inv(X.T @ (X * Wd[:, None]))
    meat = np.zeros((X.shape[1], X.shape[1]))
    for g in np.unique(clusters):
        i = clusters == g
        Xg, Wg = X[i], Wd[i]
        sw = np.sqrt(Wg)
        H = (Xg * sw[:, None]) @ bread @ (Xg * sw[:, None]).T
        ev, evec = np.linalg.eigh(np.eye(len(Wg)) - H)
        ev = np.clip(ev, 1e-12, None)
        Ag = evec @ np.diag(ev ** -0.5) @ evec.T
        eg = w[i] * (y[i] - mu[i]) / sw                 # Pearson-type residual scaled
        ug = (Xg * sw[:, None]).T @ (Ag @ eg)
        meat += np.outer(ug, ug)
    return bread @ meat @ bread

class Fit:
    def __init__(self, df, terms, y='received', family='poisson', weights=None, interact=None, cluster='community'):
        df = df.dropna(subset=[y] + [t for t in terms if t in df] + ([interact[1]] if interact else []))
        if weights is not None: weights = weights.loc[df.index]
        X = design(df, terms, interact)
        X = X.loc[:, X.std() > 0].copy(); X['const'] = 1.0
        fam = {'poisson': sm.families.Poisson(), 'binomial': sm.families.Binomial(),
               'gaussian': sm.families.Gaussian()}[family]
        m = sm.GLM(df[y].astype(float), X, family=fam, var_weights=weights).fit()
        self.df, self.X, self.m, self.family, self.y = df, X, m, family, y
        self.G = df[cluster].nunique()
        self.V = cr2_vcov(X, df[y], m.mu, df[cluster].values, family, weights)
        self.b = m.params.values
        self.se = np.sqrt(np.diag(self.V))
        self.tcrit = stats.t.ppf(0.975, self.G - 1)
        self.n = len(df); self.events = int((df[y] == 0).sum())
        self.terms, self.interact = terms, interact
        self._wts = (np.ones(len(df)) if weights is None else np.asarray(weights)) * (m.mu if family == 'poisson' else (m.mu * (1 - m.mu) if family == 'binomial' else np.ones(len(df))))
        self._cl = df[cluster].values; self._Q = None
    def _bm_setup(self):
        Xt = self.X.values * np.sqrt(self._wts)[:, None]
        B = np.linalg.inv(Xt.T @ Xt); H = Xt @ B @ Xt.T; M = np.eye(len(Xt)) - H
        parts = []
        for g in np.unique(self._cl):
            i = np.where(self._cl == g)[0]
            ev, evec = np.linalg.eigh(M[np.ix_(i, i)]); ev = np.clip(ev, 1e-12, None)
            A = evec @ np.diag(ev ** -0.5) @ evec.T
            parts.append((i, M[i, :].T @ A @ Xt[i] @ B))      # n x k block: q_g = parts @ c
        self._Q = parts
    def bm_df(self, c):
        """Bell–McCaffrey (Satterthwaite) degrees of freedom for contrast c'b under CR2 (Pustejovsky & Tipton 2018)."""
        if self._Q is None: self._bm_setup()
        c = np.asarray(c, float)
        Q = np.column_stack([P @ c for _, P in self._Q]); L = Q.T @ Q
        return float(np.trace(L) ** 2 / np.sum(L ** 2))
    def df_coef(self, j):
        e = np.zeros(len(self.b)); e[j] = 1.0; return self.bm_df(e)
    def coef(self, name):
        j = list(self.X.columns).index(name)
        b, s = self.b[j], self.se[j]; dfj = self.df_coef(j)
        p = 2 * stats.t.sf(abs(b / s), dfj)
        return b, s, p
    def coef_ci(self, name):
        j = list(self.X.columns).index(name); dfj = self.df_coef(j); t = stats.t.ppf(0.975, dfj)
        b, s = self.b[j], self.se[j]
        return np.exp(b), np.exp(b - t * s), np.exp(b + t * s), 2 * stats.t.sf(abs(b / s), dfj), dfj
    def ratio_table(self):
        rows = []
        for j, c in enumerate(self.X.columns):
            if c == 'const': continue
            b, s = self.b[j], self.se[j]; dfj = self.df_coef(j); t = stats.t.ppf(0.975, dfj)
            rows.append(dict(term=c, est=np.exp(b), lo=np.exp(b - t * s), hi=np.exp(b + t * s),
                             p=2 * stats.t.sf(abs(b / s), dfj), df=dfj))
        return pd.DataFrame(rows)
    def predict(self, df, b=None):
        X = design(df, self.terms, self.interact).reindex(columns=self.X.columns, fill_value=0.0)
        X['const'] = 1.0
        eta = X.values @ (self.b if b is None else b)
        return np.exp(eta) if self.family == 'poisson' else (1 / (1 + np.exp(-eta)) if self.family == 'binomial' else eta)
    def wald(self, names):
        idx = [list(self.X.columns).index(n) for n in names if n in self.X.columns]
        b = self.b[idx]; V = self.V[np.ix_(idx, idx)]
        F = float(b @ np.linalg.solve(V, b)) / len(idx)
        return F, len(idx), float(stats.f.sf(F, len(idx), self.G - 1))

def standardise(fit, pop, levels=(1, 2, 3), var='round', weights=None, b=None):
    """Marginal standardisation: mean predicted outcome with everyone set to each level."""
    out = {}
    for lv in levels:
        p2 = pop.copy(); p2[var] = lv
        pr = fit.predict(p2, b)
        out[lv] = np.average(pr, weights=weights)
    return out

BMDF = True
def gcomp(fit, pop, weights=None):
    """Adjusted coverage by round plus PD and PR contrasts, delta-method CIs using CR2 vcov."""
    pop = pop.dropna(subset=[t for t in fit.terms if t in pop])
    base = standardise(fit, pop, weights=weights)
    eps = 1e-6; k = len(fit.b)
    def contrasts(b):
        s = standardise(fit, pop, weights=weights, b=b)
        return np.array([s[1], s[2], s[3], s[2] - s[1], s[3] - s[1], s[3] - s[2],
                         np.log(s[2] / s[1]), np.log(s[3] / s[1]), np.log(s[3] / s[2])])
    f0 = contrasts(fit.b)
    J = np.zeros((len(f0), k))
    for j in range(k):
        bb = fit.b.copy(); bb[j] += eps
        J[:, j] = (contrasts(bb) - f0) / eps
    se = np.sqrt(np.diag(J @ fit.V @ J.T))
    names = ['cov_R1', 'cov_R2', 'cov_R3', 'PD_R2_R1', 'PD_R3_R1', 'PD_R3_R2', 'PR_R2_R1', 'PR_R3_R1', 'PR_R3_R2']
    res = {}; dfs = {}
    for i, nm in enumerate(names):
        dfi = fit.bm_df(J[i]) if BMDF else fit.G - 1; dfs[nm] = dfi
        t = stats.t.ppf(0.975, dfi)
        if nm.startswith('PR'):
            res[nm] = (np.exp(f0[i]), np.exp(f0[i] - t * se[i]), np.exp(f0[i] + t * se[i]),
                       2 * stats.t.sf(abs(f0[i] / se[i]), dfi))
        else:
            res[nm] = (f0[i], f0[i] - t * se[i], f0[i] + t * se[i],
                       2 * stats.t.sf(abs(f0[i] / se[i]), dfi) if nm.startswith('PD') else np.nan)
    res['df'] = dfs
    return res

def cluster_prop(df, y, cluster='community'):
    """Proportion with cluster-robust (ratio-estimator) logit CI, t(G-1)."""
    df = df.dropna(subset=[y]); n = len(df); p = df[y].mean()
    g = df.groupby(cluster)[y].agg(['sum', 'size'])
    G = len(g)
    var = G / (G - 1) * (((g['sum'] - p * g['size']) ** 2).sum()) / n ** 2
    se_logit = np.sqrt(var) / (p * (1 - p))
    t = stats.t.ppf(0.975, G - 1)
    lg = np.log(p / (1 - p))
    inv = lambda x: 1 / (1 + np.exp(-x))
    return dict(n=n, k=int(df[y].sum()), p=p, lo=inv(lg - t * se_logit), hi=inv(lg + t * se_logit), G=G)

