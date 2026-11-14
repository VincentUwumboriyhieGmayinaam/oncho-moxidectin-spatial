"""
Step 8 - Results report for Paper 5 (Word): all APA-style tables and figures written directly from p5_results.pkl.
Table and figure helpers are shared with Paper 3 (apa_helpers.py).

Usage
    python -I 08_results_report.py <p5_results.pkl> <figures_folder> <out.docx> <apa_helpers.py>
"""

import sys, json

src = open(sys.argv[4]).read()
src = src[: src.index("# ------------------------------------------------------------------ pull numbers")]
exec(
    src
)  # shared APA/Lancet helpers from Paper 3 (doc, f, pc, ci, pv, est, H, P, apa_table, figure, new_section)
import numpy as np, pandas as pd

CODE = json.load(open(__import__("os").environ.get("COMMUNITY_KEY", "data/community_codes.json")))
import pickle as _pk, os as _os

SV = _pk.load(
    open(_os.path.join(_os.path.dirname(sys.argv[1]), "scan_validation", "scan_validation.pkl"), "rb")
)
cd = lambda names: ", ".join(CODE.get(n, n) for n in names)
t1 = R["table1"]
ag = R["agreement"].set_index("var")
N = R["n"]
RV = R["rev"]
CS = RV["comm_scan"]
M2 = RV["moran2"]
PE = RV["persistence"]
PL = RV["persistent"]
S = RV["sens"]
m1 = {m["var"]: m for m in RV["model1"]}
GEE = RV["gee"]
ECO = RV["eco"]
SC_old = R["scan"]
OSM = R.get("osm_n") is not None and "d_osm" in ag.index
REASON = {1: "not at home", 2: "refused", 3: "not eligible", 4: "distributor never came", 5: "other"}
RND = {1: "Round 1 (ivermectin)", 2: "Round 2 (moxidectin)", 3: "Round 3 (moxidectin)"}


def prs(t):
    return f'{f(t["est"], 2)} ({ci(t["lo"], t["hi"], 2)})'


def rowpr(df, term):
    r = df.set_index("term").loc[term]
    return prs(r), pv(r.p)


def rtxt(rs):
    if not isinstance(rs, dict) or not rs:
        return "—"
    return "; ".join(f"{REASON.get(int(k), k)} {v}" for k, v in sorted(rs.items(), key=lambda kv: -kv[1]))


# ================================================================== TITLE
p = doc.add_paragraph()
r = p.add_run(
    "Spatial clustering, between-community variation and persistence of community participation, and its relation to black-fly exposure, during ivermectin and moxidectin mass drug administration for onchocerciasis in Twifo Atti-Morkwa, Ghana: results"
)
r.bold = True
r.font.size = Pt(14)
P(
    "Paper 5 · Results report (revised after internal peer review): statistical methods summary, APA tables, figures and narrative. Interpretation is descriptive and associational; no causal claims are made. Communities are shown by code (C01–C22); the key is held by the study team.",
    italic=True,
    size=10,
)

# ================================================================== METHODS
H("Statistical methods (summary)")
P(
    f'**Design and data.** Three independent cross-sectional household surveys (400 respondents per round) followed one round of ivermectin (Round 1) and two of moxidectin (Rounds 2 and 3); respondents are not linked across rounds. Community participation was defined among respondents who recalled the distribution (Round 1, {CS[1][0.25]["N"]}; Round 2, {CS[2][0.25]["N"]}; Round 3, {CS[3][0.25]["N"]}). Black-fly season, time of day, river characteristics and river activities were asked only in Round 3 (dry season), so exposure–participation analyses use Round 3 respondents with a valid GPS point who recalled the distribution (n = {N["A3g"]}). Perceived black-fly presence and self-reported time to the river were asked in all rounds.'
)
P(
    "**Spatial units.** The spatial scan used household GPS points, so that clusters can be smaller or larger than a single community. Moran’s I, Gi∗ statistics and persistence used community centroids (median of household points), because about 20 respondents per community are too few for household-level autocorrelation measures."
)
P(
    "**Global clustering.** Moran’s I on raw and empirical-Bayes (EB) smoothed community participation under k-nearest-neighbour weights (k = 4 primary; k = 3, 5 and inverse distance as sensitivity); two-sided permutation p values from 9,999 permutations. Local Getis–Ord Gi∗ statistics were computed (9,999 conditional permutations)."
)
P(
    "**Spatial scan.** Clusters of excess non-participation were sought with the Kulldorff Bernoulli spatial scan statistic, with circular windows centred on each of the 226 public settlement points, a maximum window of 25% of respondents and 999 Monte Carlo replicates; the two most likely non-overlapping clusters per round are reported. The Monte Carlo null relabels non-participants among respondents and so treats respondents as independent. Because participation is correlated within communities, these p values may be too small. As a sensitivity analysis, the scan was repeated at community level with a null that permutes whole communities (windows = a community centroid and its nearest neighbours; 10%, 25% and 50% maximum windows), which tests whether low-participation communities lie closer together than expected. Its code was checked against an independent brute-force implementation and its calibration and power were assessed by simulation."
)
P(
    "**Persistence.** Community participation was compared across rounds with Spearman ρ (95% CI by Fisher transformation with the Bonett–Wright standard error). Communities were classed by the number of rounds below the 80% programme threshold; only communities sampled in all three rounds could be classed as persistently low."
)
P(
    "**Exposure–participation associations (Round 3).** Modified Poisson regression with cluster-robust (CR2) variance and Bell–McCaffrey (Satterthwaite) degrees of freedom per coefficient. With 53 non-participants, adjustment was restricted to age group (3 levels), sex, permanent residence and a continuous wealth index. Each exposure was modelled separately (nine exposures; results read as a family, not as isolated tests). Sensitivity analyses: exchangeable GEE logistic models; community-level (ecological) Spearman correlations; a natural cubic spline of log distance (3 df; adjusted for perceived black flies and the original, fuller covariate set) with standardised participation shown only between the 5th and 95th percentiles of household distance; and residual Moran’s I at household and community level."
)
P(
    "**Deviations from the analysis plan.** (1) Community maps replaced a continuous geostatistical surface (20–22 communities). (2) Self-reported time and mapped distance were analysed as separate exposures because they disagreed. (3) After review, Moran’s I tests were made two-sided, a community-level scan was added as a sensitivity analysis, the adjustment set for exposure models was reduced, the exposure-index quadrant classification was replaced by a persistence classification, and exploratory analyses of knowledge and side effects were removed. Acceptability was not analysed."
)

# ================================================================== RESULTS narrative
H("Results")
tot = t1[t1.community == "All communities"].iloc[0]
cm = t1[t1.community != "All communities"]
rd = RV["river_dries_n"]
P(
    f'Of {N["R3"]} Round 3 respondents in {len(cm)} communities, {f(tot.flies, 1)}% reported black flies in their community and {f(tot.flies_def, 1)}% answered “yes, definitely”. Most of those reporting flies said they occurred mainly in the wet season ({f(100 * R["fly_season"][1.0], 1)}%) and in the morning ({f(100 * R["fly_time"][1.0], 1)}%); the survey itself took place in the dry season. Nearly all reported a fast-flowing river nearby ({f(tot.fast, 1)}%), and farming was the main river activity ({f(tot.agri, 1)}%). The question on whether the river dries was answered by {rd[1]} of {N["R3"]} respondents. Perceived black-fly presence ranged from {f(cm.flies.min(), 0)}% to {f(cm.flies.max(), 0)}% across communities (Table 1; Figure 1). Median household distance to a larger river was {f(tot.d_big, 2)} km (community medians {f(cm.d_big.min(), 2)} to {f(cm.d_big.max(), 2)} km); the median self-reported round trip was {f(R["self_minutes"][0], 0)} minutes (IQR {f(R["self_minutes"][1], 0)}–{f(R["self_minutes"][2], 0)}).'
)
a1 = ag.loc["d_big"]
a2 = ag.loc["d_hr"]
P(
    f'Self-reported time to the river agreed poorly with mapped distance (Table 2). For larger rivers the household correlation was inverse (ρ {f(a1.rho, 2)}, 95% CI {ci(a1.lo, a1.hi, 2)}; weighted κ {f(a1.kappa, 2)}); for any HydroRIVERS channel it was {f(a2.rho, 2)} ({ci(a2.lo, a2.hi, 2)}). The OpenStreetMap network within the district totalled {f(RV["osm_len_km"], 0)} km of waterways against {f(RV["hr_len_km"], 0)} km in HydroRIVERS, so small streams that respondents may have had in mind are largely unmapped.'
    + (
        f' Against OpenStreetMap waterways, ρ was {f(ag.loc["d_osm"].rho, 2)} ({ci(ag.loc["d_osm"].lo, ag.loc["d_osm"].hi, 2)}).'
        if OSM
        else ""
    )
)
k = {r_: M2[r_][("knn4", "eb")] for r_ in (1, 2, 3)}
kr = {r_: M2[r_][("knn4", "raw")] for r_ in (1, 2, 3)}
cr = R["rev"]["comm_round"]
nlow = {r_: int((cr[r_] < 0.8).sum()) for r_ in (1, 2, 3)}
ncom = {r_: int(cr[r_].notna().sum()) for r_ in (1, 2, 3)}
H1 = SC_old[1]["clusters"][0]
H2 = SC_old[2]["clusters"][0]
H3a, H3b = SC_old[3]["clusters"][0], SC_old[3]["clusters"][1]
c1 = CS[1][0.25]["clusters"][0]
c3 = CS[3][0.25]["clusters"][0]
P(
    f'Community participation varied widely within every round. It ranged from {pc(cr[1].min(), 0)}% to {pc(cr[1].max(), 0)}% in Round 1, {pc(cr[2].min(), 0)}% to {pc(cr[2].max(), 0)}% in Round 2 and {pc(cr[3].min(), 0)}% to {pc(cr[3].max(), 0)}% in Round 3, and {nlow[1]}, {nlow[2]} and {nlow[3]} of {ncom[1]} communities were below the 80% threshold (communities with at least five respondents who recalled the distribution; Table 4; Figure 3). The intraclass correlation of non-participation in Round 3 was {f(SV["sim"]["rho"], 2)}, so about a fifth of the variation in non-participation lay between communities.'
)
P(
    f'Non-participation was spatially clustered (Table 3; Figure 2). The spatial scan identified a borderline cluster in the ivermectin round, covering {cd(H1["communities"])} ({H1["obs"]} of {int(H1["n"])} respondents not participating; relative risk [RR] {f(H1["rr"], 2)}; p = {f(H1["p"], 3)}). In Round 2 a cluster was centred on {cd(H2["communities"])} ({H2["obs"]} of {int(H2["n"])}; RR {f(H2["rr"], 2)}; p = {pv(H2["p"])}). In Round 3 two clusters were significant: {cd(H3a["communities"])} ({H3a["obs"]} of {int(H3a["n"])}; RR {f(H3a["rr"], 2)}; p = {pv(H3a["p"])}) and {cd(H3b["communities"])} ({H3b["obs"]} of {int(H3b["n"])}; RR {f(H3b["rr"], 2)}; p = {pv(H3b["p"])}). C12 fell within the most likely cluster in all three rounds, together with its neighbours C04 and C11 in Rounds 1 and 3; C11, C12 and C13, all within Round 3 clusters, were also the only communities below 80% in every round. Local Gi∗ statistics were nominally significant for two high-participation communities in Round 1 and one low-participation community in Round 2, and for none in Round 3.'
)
P(
    f'Global spatial autocorrelation between neighbouring communities, measured with Moran’s I on community centroids, was evident only in Round 1 (Table 3). Moran’s I for EB-smoothed participation was {f(k[1]["I"], 2)} in Round 1 (two-sided p = {pv(k[1]["p2"])}; raw {f(kr[1]["I"], 2)}, p = {pv(kr[1]["p2"])}), {f(k[2]["I"], 2)} in Round 2 (p = {pv(k[2]["p2"])}) and {f(k[3]["I"], 2)} in Round 3 (p = {pv(k[3]["p2"])}). The Round 1 result was sensitive to the weights (inverse distance, p = {pv(M2[1][("idw", "eb")]["p2"])}).'
)
pr = PE["R1-R3"]
p12 = PE["R1-R2"]
p23 = PE["R2-R3"]
low3 = PL[PL.status == "Below 80% in all three rounds"]
low2 = PL[PL.status == "Below 80% in two rounds"]
sv = SV["sim"]
P(
    f'In the community-level sensitivity analysis (Table S3), which asks whether low-participation communities lie next to each other more than expected once communities are allowed to differ, the most likely Round 1 window again covered {", ".join(sorted(c1["codes"]))} (p = {f(c1["p"], 3)}) and the Round 3 window covered {" and ".join(sorted(c3["codes"]))} (p = {pv(c3["p"])}); no window reached p<0·05. In simulations (Table S4), this test had nominal type I error ({pc(sv["typeI"]["perm"])}%) but low power, detecting a planted cluster of three neighbouring communities with 15, 25 and 35 percentage points higher non-participation in {pc(sv["power"][0.15]["perm"], 0)}%, {pc(sv["power"][0.25]["perm"], 0)}% and {pc(sv["power"][0.35]["perm"], 0)}% of data sets, whereas the household-level scan gave p<0·05 in {pc(sv["typeI"]["bern"])}% of data sets with between-community variation but no spatial clustering. The household-level clusters therefore identify where non-participation was concentrated, largely reflecting low-participation communities, while evidence that neighbouring communities share low participation beyond this is limited.'
)
P(
    f'Community participation was moderately persistent between Round 1 and Round 3 (ρ {f(pr[0], 2)}, 95% CI {ci(pr[1], pr[2], 2)}; {pr[4]} communities), less so between adjacent rounds (Round 1–2, {f(p12[0], 2)} [{ci(p12[1], p12[2], 2)}]; Round 2–3, {f(p23[0], 2)} [{ci(p23[1], p23[2], 2)}]). Of {int((PL.rounds == 3).sum())} communities sampled in all rounds, {len(low3)} ({", ".join(low3.code)}) were below 80% in all three rounds and {len(low2)} in two (Table 4; Figure 3). The three persistently low communities had Round 3 participation of {pc(low3[3].min(), 0)}–{pc(low3[3].max(), 0)}%; they differed in perceived black-fly presence ({pc(low3.flies.min(), 0)}–{pc(low3.flies.max(), 0)}%) and distance to a larger river ({f(low3.d_big.min(), 1)}–{f(low3.d_big.max(), 1)} km). Among their Round 3 non-participants, the commonest reasons were being away from home and being judged not eligible.'
)
mq = m1["dq_big"]
mf = m1["blackflies_yes"]
ma = m1["river_agri"]
q4, _ = rowpr(mq["adj"], "dq_big=4")
fl, flp = rowpr(mf["adj"], "blackflies_yes")
ag_, agp = rowpr(ma["adj"], "river_agri")
lv = ma["levels"]
P(
    f'In Round 3, community participation was not clearly associated with any exposure, and estimates were imprecise (Table 5; {mq["events"]} non-participants among {mq["n"]} respondents). Compared with the nearest quartile of distance to a larger river, the adjusted PR for the farthest quartile was {q4} (joint p = {pv(mq["wald"][2])}). The adjusted PR for perceiving black flies was {fl}. Farming as the main river activity had an adjusted PR of {ag_} (p = {agp}); its reference group was small ({int(lv.iloc[0, 0])} of {int(lv.iloc[0, 1])} participating). GEE models and community-level correlations agreed (distance ρ {f(ECO["dist"][0], 2)}, 95% CI {ci(ECO["dist"][1], ECO["dist"][2], 2)}; black flies ρ {f(ECO["flies"][0], 2)}, {ci(ECO["flies"][1], ECO["flies"][2], 2)}). The standardised spline was compatible with no trend (p = {pv(R["model2_spline_wald"][2])}; Figure 4A).'
)
rm = R["resid_moran"]
rmc = RV["resid_moran_comm"]
P(
    f'After adjustment, household-level residuals remained spatially autocorrelated (Moran’s I {f(rm["I"], 2)}; p = {pv(rm["p"])}), consistent with clustering of non-participation, whereas community-mean residuals were not (I {f(rmc["I"], 2)}; two-sided p = {pv(rmc["p2"])}). Sensitivity analyses gave similar estimates (Table 6) with imputed GPS, after excluding the one flagged GPS point in the analytic sample and when perceived black flies were pooled across rounds (aPR {est(S["allrounds_flies"][0])}; n = {S["allrounds_flies"][1]:,}). Counting non-recallers as non-participants moved the farthest-quartile aPR to {est(S["lower"]["q4"])}, still with a CI including 1.'
)

# ================================================================== TABLES
new_section(True)
rows = []
cm2 = cm.assign(code=cm.community.map(CODE)).sort_values("d_big")
for _, r in pd.concat([cm2, t1[t1.community == "All communities"].assign(code="All communities")]).iterrows():
    rows.append(
        [
            r.code,
            f"{int(r.n)}",
            f"{int(r.n_gps)}",
            f(r.flies, 1),
            f(r.flies_def, 1),
            f(r.wet, 1),
            f(r.fast, 1),
            f(r.dries, 1),
            f(r.agri, 1),
            f(r.self_min, 0),
            f(r.d_big, 2),
            f(r.d_hr, 2),
        ]
        + ([f(r.d_osm, 2) if pd.notna(r.d_osm) else "—"] if OSM else [])
        + [f(r.receipt, 1)]
    )
hdr = (
    [
        "Community",
        "n",
        "GPS n",
        "Black flies %",
        "“Definitely” %",
        "Wet season %",
        "Fast river %",
        "River dries %",
        "Farming %",
        "Self-report min",
        "Larger river km",
        "Any river km",
    ]
    + (["OSM stream km"] if OSM else [])
    + ["Participation %"]
)
apa_table(
    1,
    "Perceived and Mapped Black-Fly Exposure and Community Participation by Community, Round 3 (Moxidectin, Dry Season)",
    hdr,
    rows,
    f"Communities ordered by median distance to the nearest larger river (Strahler order ≥3, HydroRIVERS). Black flies % = “yes, a bit” or “yes, definitely”; “don’t know” excluded. Season and river items asked in Round 3 only. River dries % among {rd[1]} respondents who answered. Self-report min = median self-reported round-trip time to river. Distances are household medians. Participation % among all respondents who recalled the distribution (overall 299/362, 82·6%); in the exposure analytic sample with a valid GPS point it was 273/326 (83·7%). C02 and C08 had four valid GPS points each, so their distances are imprecise.",
    widths=[2.4, 0.9, 1.1, 1.4, 1.5, 1.4, 1.3, 1.4, 1.3, 1.5, 1.5, 1.4] + ([1.4] if OSM else []) + [2.1],
    bold_rows=(len(rows) - 1,),
    font=8.5,
    landscape=True,
)
rows = []
for v in ag.index:
    a = ag.loc[v]
    zc = np.arctanh(a.rho_comm)
    sc = 1.06 / np.sqrt(a.n_comm - 3)
    rows.append(
        [
            a.measure,
            f"{f(a.median_km, 2)} ({f(a.iqr[0], 2)}–{f(a.iqr[1], 2)})",
            f"{f(a.rho, 2)} ({ci(a.lo, a.hi, 2)})",
            f(a.kappa, 2),
            f"{f(a.rho_comm, 2)} ({ci(np.tanh(zc - 1.96 * sc), np.tanh(zc + 1.96 * sc), 2)})",
            pv(a.p_comm),
            f"{int(a.n)}/{int(a.n_comm)}",
        ]
    )
apa_table(
    2,
    "Agreement Between Self-Reported Round-Trip Time to River and Mapped Distance to River, Round 3",
    [
        "Mapped network",
        "Median km (IQR)",
        "Household ρ (95% CI)",
        "Weighted κ",
        "Community ρ (95% CI)",
        "p",
        "n / communities",
    ],
    rows,
    f'ρ = Spearman correlation; 95% CI from 2,000 community-cluster bootstrap resamples. κ = quadratic-weighted kappa between quartiles. Community ρ 95% CI by Fisher transformation. Positive values indicate agreement; negative values indicate inverse ranking. n = 355 because one of the 356 respondents with a valid GPS point did not report a travel time. Waterway length within the district: HydroRIVERS {f(RV["hr_len_km"], 0)} km; OpenStreetMap {f(RV["osm_len_km"], 0)} km.',
    widths=[5, 2.6, 3, 1.5, 2.6, 1.1, 2],
)
rows = []
bold = []
for r_ in (1, 2, 3):
    bold.append(len(rows))
    rows.append(
        [
            f'{RND[r_]} — {CS[r_][0.25]["G"]} communities; {CS[r_][0.25]["C"]} of {CS[r_][0.25]["N"]} not participating',
            "",
            "",
            "",
            "",
        ]
    )
    for cl in SC_old[r_]["clusters"][:2]:
        rows.append(
            [
                f'Scan cluster: {cd(cl["communities"])} (radius {f(cl["radius_km"], 1)} km)',
                f'{cl["obs"]}/{int(cl["n"])}',
                f'RR {f(cl["rr"], 2)}',
                pv(cl["p"]),
                "",
            ]
        )
    for w, wl in [
        ("knn4", "k = 4 (primary)"),
        ("knn3", "k = 3"),
        ("knn5", "k = 5"),
        ("idw", "inverse distance"),
    ]:
        e, rw = M2[r_][(w, "eb")], M2[r_][(w, "raw")]
        rows.append([f"Moran’s I, {wl}", f(e["I"], 2), pv(e["p2"]), f(rw["I"], 2), pv(rw["p2"])])
    g = M2[r_]["gi"]
    gs = g[g.p < 0.05]
    rows.append(
        [
            "Gi∗ nominal p<0·05",
            ", ".join(f'{c_} ({"high" if z_ > 0 else "low"})' for c_, z_ in zip(gs.code, gs.z)) or "none",
            "",
            "",
            "",
        ]
    )
apa_table(
    3,
    "Spatial Clustering of Non-Participation and Community Participation by Survey Round",
    ["Statistic", "Observed/n, or EB I", "RR, or EB p", "Scan p, or raw I", "Raw p"],
    rows,
    "Scan = Kulldorff Bernoulli spatial scan for excess non-participation using household locations; circular windows centred on 226 public settlement points; maximum 25% of respondents; 999 Monte Carlo replicates; two most likely non-overlapping clusters shown. Observed/n = non-participants/respondents in the window; RR = risk of non-participation inside vs outside. The Monte Carlo null treats respondents as independent; see Table S3 for a community-level sensitivity analysis. Moran’s I on empirical-Bayes (EB) smoothed and raw community participation (community centroids); two-sided p from 9,999 permutations. Gi∗ = Getis–Ord local statistic; nominal p, not corrected for 20–21 tests per round.",
    widths=[8.0, 3.2, 2.4, 2.6, 1.6],
    bold_rows=tuple(bold),
    indent_rows=tuple(i for i in range(len(rows)) if i not in bold),
    font=8.5,
)
rows = []
bold = []
for stt in [
    "Below 80% in all three rounds",
    "Below 80% in two rounds",
    "Below 80% in at most one round",
    "Not sampled in all rounds",
]:
    sub = PL[PL.status == stt].sort_values("code")
    if not len(sub):
        continue
    bold.append(len(rows))
    rows.append([f"{stt} ({len(sub)})", "", "", "", "", "", "", "", ""])
    for c_, r in sub.iterrows():
        cell = lambda x: pc(x, 0) if pd.notna(x) else "—"
        rows.append(
            [
                r.code,
                cell(r[1]),
                cell(r[2]),
                cell(r[3]),
                cell(r.flies),
                f(r.d_big, 1) if pd.notna(r.d_big) else "—",
                cell(r.nonperm),
                f"{int(r.gps_n)}" if pd.notna(r.gps_n) else "—",
                rtxt(r.reasons),
            ]
        )
apa_table(
    4,
    "Persistence of Community Participation Across Survey Rounds and Round 3 Characteristics of Communities",
    [
        "Community",
        "Round 1 %",
        "Round 2 %",
        "Round 3 %",
        "Black flies %",
        "Larger river km",
        "Not permanent residents %",
        "GPS n",
        "Round 3 reasons for non-participation (n)",
    ],
    rows,
    f"Participation among respondents who recalled the distribution (about 20 per community per round, so single-community percentages are imprecise). Black flies, distance (household median), residence, GPS n and reasons refer to Round 3. Spearman ρ of community participation: Round 1 vs 3, {f(pr[0], 2)} ({ci(pr[1], pr[2], 2)}); Round 1 vs 2, {f(p12[0], 2)} ({ci(p12[1], p12[2], 2)}); Round 2 vs 3, {f(p23[0], 2)} ({ci(p23[1], p23[2], 2)}); 95% CIs by Fisher transformation.",
    widths=[3.4, 1.6, 1.6, 1.6, 1.8, 1.9, 2.2, 1.3, 6.5],
    bold_rows=tuple(bold),
    indent_rows=tuple(i for i in range(len(rows)) if i not in bold),
    font=8.5,
    landscape=True,
)
E = R["big_edges"]
LEV = {
    "dq_big": [
        f"Q1, <{f(E[1], 2)} km (reference)",
        f"Q2, {f(E[1], 2)}–{f(E[2], 2)} km",
        f"Q3, {f(E[2], 2)}–{f(E[3], 2)} km",
        f"Q4, ≥{f(E[3], 2)} km",
    ],
    "dq_osm": ["Q1 (nearest; reference)", "Q2", "Q3", "Q4 (farthest)"],
    "fly_time": ["Morning (reference)", "Midday", "Evening", "All day"],
    "near_river_self": ["≤10 min (reference)", "11–30 min", "31–60 min", ">60 min"],
}
rows = []
bold = []
ind = []
for v, m in m1.items():
    if v == "dq_osm":
        continue
    bold.append(len(rows))
    rows.append([m["label"], "", "", "", "", pv(m["wald"][2])])
    lvv = m["levels"]
    names = LEV.get(v, ["No (reference)", "Yes"])
    for i, key in enumerate(lvv.index):
        s_, c_ = lvv.loc[key, "sum"], lvv.loc[key, "count"]
        ind.append(len(rows))
        if i == 0:
            rows.append([names[0], f"{int(s_)}/{int(c_)} ({pc(s_ / c_)})", "1·00", "1·00", "", ""])
            continue
        term = f"{v}={int(key)}" if v in LEV else v
        u = m["unadj"].set_index("term").loc[term]
        a = m["adj"].set_index("term").loc[term]
        rows.append([names[i], f"{int(s_)}/{int(c_)} ({pc(s_ / c_)})", prs(u), prs(a), pv(a.p), ""])
bold.append(len(rows))
rows.append(["Sensitivity: GEE (exchangeable), adjusted OR", "", "", "", "", ""])
g4 = GEE["dq_big"].loc["dq_big=4"]
gf = GEE["blackflies_yes"].loc["blackflies_yes"]
ind += [len(rows), len(rows) + 1]
rows.append(["Q4 vs Q1 distance", "", "", f"{f(g4.OR, 2)} ({ci(g4.lo, g4.hi, 2)})", pv(g4.p), ""])
rows.append(["Black flies perceived", "", "", f"{f(gf.OR, 2)} ({ci(gf.lo, gf.hi, 2)})", pv(gf.p), ""])
apa_table(
    5,
    "Associations of Perceived and Mapped Black-Fly Exposure With Community Participation, Round 3",
    ["Exposure", "Participated/n (%)", "Crude PR (95% CI)", "Adjusted PR (95% CI)", "p", "Joint p"],
    rows,
    f'PR = prevalence ratio from modified Poisson regression with CR2 cluster-robust variance (20 communities) and Bell–McCaffrey degrees of freedom. Adjusted for age group (15–24, 25–44, ≥45 years), sex, permanent residence and wealth index (continuous); {mq["events"]} non-participants among {mq["n"]} respondents. Each exposure modelled separately; nine exposures in total, so isolated p values near 0·05 should not be over-read. Joint p = adjusted Wald test. Distance quartile cut-points were taken from all 356 Round 3 respondents with a valid GPS point, so quartile sizes in the analytic sample are unequal. Community-level Spearman ρ of Round 3 participation with median distance {f(ECO["dist"][0], 2)} ({ci(ECO["dist"][1], ECO["dist"][2], 2)}) and with % perceiving black flies {f(ECO["flies"][0], 2)} ({ci(ECO["flies"][1], ECO["flies"][2], 2)}).',
    widths=[6.3, 2.6, 2.8, 2.8, 1.2, 1.3],
    bold_rows=tuple(bold),
    indent_rows=tuple(ind),
    font=8.5,
)
rows = []
lab = {
    "main": "Main analysis (valid GPS)",
    "imputed": "Missing GPS imputed (community median)",
    "no_flagged": "Flagged GPS point excluded",
    "lower": "Non-recall counted as not participating",
    "upper": "Non-recall counted as participating",
    "osm": "OpenStreetMap distance quartiles",
}
for k_ in ["main", "imputed", "no_flagged", "lower", "upper"] + (["osm"] if "osm" in S else []):
    s_ = S[k_]
    rows.append(
        [
            lab[k_],
            f'{s_["n_d"]}',
            est(s_["q4"]),
            pv(s_["q_wald"]),
            est(s_["flies"]) if k_ != "osm" else "not applicable",
        ]
    )
rows.append(
    [
        "Black flies, all three rounds pooled (round-adjusted)",
        f'{S["allrounds_flies"][1]:,}',
        "—",
        "—",
        est(S["allrounds_flies"][0]),
    ]
)
apa_table(
    6,
    "Sensitivity Analyses for the Main Exposure–Participation Associations",
    ["Analysis", "n", "Q4 vs Q1 distance, aPR (95% CI)", "Joint p", "Black flies, aPR (95% CI)"],
    rows,
    "aPR = adjusted prevalence ratio (covariates as in Table 5). Q4 vs Q1 = farthest vs nearest quartile of distance to a larger river. Black-fly models use one respondent fewer than distance models (one missing response). The OpenStreetMap quartiles show a non-monotonic pattern without a distance gradient, consistent with uneven mapping of small streams.",
    widths=[6.5, 1.3, 3.6, 1.3, 3.4],
)
rows = []
bold = []
for r_ in (1, 2, 3):
    bold.append(len(rows))
    rows.append([RND[r_], "", "", ""])
    for mf_ in (0.10, 0.25, 0.50):
        c = CS[r_][mf_]["clusters"][0]
        rows.append(
            [
                f'Max {int(mf_ * 100)}%: {", ".join(sorted(c["codes"]))}',
                f'{c["obs"]}/{c["n"]}',
                f(c["rr"], 2),
                pv(c["p"]),
            ]
        )
apa_table(
    "S3",
    "Community-Level Spatial Scan of Non-Participation (Sensitivity Analysis)",
    ["Most likely window", "Non-participants/n", "RR", "p"],
    rows,
    "Kulldorff Bernoulli scan on community totals; windows = a community centroid plus its nearest neighbours up to the stated share of respondents; null from 999 permutations of community (non-participants, respondents) pairs across locations (seed 11). This null keeps each community’s participation fixed and asks only whether low-participation communities lie closer together than expected; a single-community window cannot be significant, and power is low (Table S4).",
    widths=[7, 2.6, 1.4, 1.4],
    bold_rows=tuple(bold),
    indent_rows=tuple(i for i in range(len(rows)) if i not in bold),
)

rows = []
ck = SV["check"]
for _, r in ck.iterrows():
    rows.append(
        [
            RND[int(r["round"])],
            f"{int(r.maxfrac * 100)}%",
            r.codes_main,
            f(r.llr_main, 4),
            r.codes_brute,
            f(r.llr_brute, 4),
            "Yes" if r.match else "No",
        ]
    )
rows.append(["Simulation", "", "", "", "", "", ""])
rows.append(
    ["Type I error, community-permutation scan", "25%", "", "", "", pc(sv["typeI"]["perm"]) + "%", ""]
)
rows.append(["Type I error, standard Bernoulli scan", "25%", "", "", "", pc(sv["typeI"]["bern"]) + "%", ""])
for dl in (0.15, 0.25, 0.35):
    rows.append(
        [
            f"Power, planted cluster +{int(dl * 100)} points (community-permutation)",
            "25%",
            "",
            "",
            "",
            pc(sv["power"][dl]["perm"], 0) + "%",
            "",
        ]
    )
apa_table(
    "S4",
    "Validation, Calibration and Power of the Spatial Scan",
    ["Analysis", "Max window", "Main code: window", "LLR", "Brute force: window", "LLR or rate", "Match"],
    rows,
    f'LLR = log-likelihood ratio of the most likely window. Brute force = independent enumeration of every window (each community centroid plus its nearest neighbours). Simulations used Round 3 community sizes and locations; non-participation drawn from a beta-binomial distribution with the observed mean ({pc(sv["p_hat"])}%) and intraclass correlation ({f(sv["rho"], 2)}); {sv["nsim"]} null data sets and 300 per power scenario; 199 permutations per test. Standard Bernoulli = SaTScan-type null, non-participants relabelled at random among all respondents. Planted cluster = {", ".join(sorted(sv["planted"]))}.',
    widths=[6.4, 1.6, 3.2, 1.4, 3.2, 1.8, 1.2],
    bold_rows=(len(ck),),
    font=8.5,
)

# ================================================================== FIGURES
new_section(False)
figure(
    1,
    "Study Area, River Network and Perceived Black-Fly Presence by Surveyed Community, Round 3",
    f"{FIG}/Figure1_study_area_exposure.png",
    "Twifo Atti-Morkwa District, Central Region, Ghana (inset). Rivers from HydroRIVERS v1.0, line width by Strahler order; the Pra River (order 6) bisects the district."
    + (" Pale lines are OpenStreetMap small streams." if OSM else "")
    + " Grey dots are the 226 settlements in the official settlement file. Circles show surveyed community centroids, labelled by code (household coordinates are not shown, to protect confidentiality), shaded by the percentage of Round 3 respondents reporting black flies. UTM zone 30N.",
    width=16,
)
figure(
    2,
    "Community Participation and Spatial Scan Clusters of Non-Participation by Survey Round",
    f"{FIG}/Figure2_receipt_clusters_by_round.png",
    "Panels A–C show each independent survey round. Orange circles mark communities with participation below the 80% programme threshold (labelled with code and participation among respondents who recalled the distribution); grey circles, 80% or above. Black circles are Kulldorff Bernoulli scan clusters of excess non-participation based on household locations (solid, p<0·05; dashed, 0·05≤p<0·10), drawn around public settlement points; shaded windows are significant. Scan p values treat respondents as independent (see Table S3 for a community-level sensitivity analysis). Rivers and settlements as in Figure 1.",
    width=16,
)
figure(
    3,
    "Community Participation Across Three Survey Rounds",
    f"{FIG}/Figure3_persistence_by_community.png",
    "Each line is a community sampled in at least two rounds. Dark orange, below 80% in all three rounds; light orange, below 80% in two rounds; grey, other communities. Each point is based on about 20 respondents, so single-community changes between rounds are imprecise. Respondents differ between rounds.",
    width=15,
)
figure(
    4,
    "Standardised Community Participation by Distance to the Nearest Larger River, and Agreement Between Self-Reported and Mapped Distance, Round 3",
    f"{FIG}/Figure4_distance_receipt_and_agreement.png",
    "Panel A: participation standardised to the sample covariate distribution from a modified Poisson model with a natural cubic spline of log distance (3 df), adjusted for perceived black flies and covariates; band = 95% CI. The curve is shown between the 5th and 95th percentiles of household distance (rug). The overall spline test was not significant. Panel B: community median self-reported round-trip time to river against community median mapped distance to a larger river.",
    width=16,
)
doc.save(OUTF)
print("saved", OUTF)
