"""
APA table and figure helpers shared with the Paper 3 repository (this is the Paper 3 report script; 08_results_report.py
executes only the helper part, up to the line marked 'pull numbers').
"""

import sys, pickle
import numpy as np, pandas as pd
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_ORIENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

R = pickle.load(open(sys.argv[1], "rb"))
FIG = sys.argv[2]
OUTF = sys.argv[3]
S = R["sens"]


# ------------------------------------------------------------------ number formatting (Lancet: mid-dot decimals)
def f(x, d=1):
    s = f"{abs(x):.{d}f}".replace(".", "·")
    return ("−" if x < 0 and float(f"{abs(x):.{d}f}") != 0 else "") + s


def pc(x, d=1):
    return f(100 * x, d)


def ci(lo, hi, d=1, scale=1):
    return (
        f"{f(lo * scale, d)} to {f(hi * scale, d)}"
        if (lo * scale < 0)
        else f"{f(lo * scale, d)}–{f(hi * scale, d)}"
    )


def pv(p):
    if p is None or (isinstance(p, float) and np.isnan(p)):
        return ""
    if p < 0.001:
        return "<0·001"
    return f(p, 3) if p < 0.01 else f(p, 2)


def est(t, d=2, scale=1):  # (est, lo, hi, ...)
    return f"{f(t[0] * scale, d)} ({ci(t[1], t[2], d, scale)})"


# ------------------------------------------------------------------ document setup
doc = Document()
st = doc.styles["Normal"]
st.font.name = "Times New Roman"
st.font.size = Pt(12)
st.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
st.paragraph_format.space_after = Pt(6)
st.paragraph_format.line_spacing = 1.5
for s_ in doc.sections:
    s_.page_width, s_.page_height = Cm(21.0), Cm(29.7)
    s_.left_margin = s_.right_margin = Cm(2.3)
    s_.top_margin = s_.bottom_margin = Cm(2.3)
TABLE_W = 24.5
from docx.enum.section import WD_SECTION


def new_section(landscape):
    sec = doc.add_section(WD_SECTION.NEW_PAGE)
    sec.orientation = WD_ORIENT.LANDSCAPE if landscape else WD_ORIENT.PORTRAIT
    sec.page_width, sec.page_height = (Cm(29.7), Cm(21.0)) if landscape else (Cm(21.0), Cm(29.7))
    sec.left_margin = sec.right_margin = Cm(2.3)
    sec.top_margin = sec.bottom_margin = Cm(2.0)


def H(text, lvl=1):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(14 if lvl == 0 else (12.5 if lvl == 1 else 12))
    r.italic = lvl == 2
    p.paragraph_format.space_before = Pt(12 if lvl < 2 else 8)
    p.paragraph_format.keep_with_next = True
    return p


def P(text, italic=False, size=None, after=6):
    p = doc.add_paragraph()
    for chunk, b, i in parse(text):
        r = p.add_run(chunk)
        r.bold = b
        r.italic = i or italic
        if size:
            r.font.size = Pt(size)
    p.paragraph_format.space_after = Pt(after)
    return p


def parse(text):
    """minimal **bold** / *italic* parser"""
    out, i, b, it, buf = [], 0, False, False, ""
    while i < len(text):
        if text.startswith("**", i):
            out.append((buf, b, it))
            buf = ""
            b = not b
            i += 2
            continue
        if text[i] == "*" and not text.startswith("**", i):
            out.append((buf, b, it))
            buf = ""
            it = not it
            i += 1
            continue
        buf += text[i]
        i += 1
    out.append((buf, b, it))
    return [o for o in out if o[0]]


def set_cell_border(cell, **kw):
    tcPr = cell._tc.get_or_add_tcPr()
    b = tcPr.find(qn("w:tcBorders"))
    if b is None:
        b = OxmlElement("w:tcBorders")
        tcPr.append(b)
    for edge in ("top", "bottom", "left", "right"):
        if edge in kw:
            el = b.find(qn(f"w:{edge}"))
            if el is None:
                el = OxmlElement(f"w:{edge}")
                b.append(el)
            for k, v in kw[edge].items():
                el.set(qn(f"w:{k}"), str(v))


NONE = dict(val="nil")
LINE = dict(val="single", sz=8, color="000000")
THIN = dict(val="single", sz=4, color="000000")


def apa_table(
    num,
    title,
    header,
    rows,
    note,
    widths=None,
    bold_rows=(),
    indent_rows=(),
    font=9,
    header2=None,
    landscape=False,
):
    """APA 7 table: bold number, italic title, horizontal rules only, notes below."""
    p = doc.add_paragraph()
    r = p.add_run(f"Table {num}")
    r.bold = True
    if num not in (1,):
        p.paragraph_format.page_break_before = True
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.line_spacing = 1.0
    p = doc.add_paragraph()
    r = p.add_run(title)
    r.italic = True
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.line_spacing = 1.15
    hdrs = [header2, header] if header2 else [header]
    t = doc.add_table(rows=len(hdrs) + len(rows), cols=len(header))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    allrows = hdrs + rows
    for i, row in enumerate(allrows):
        cells = t.rows[i].cells
        for j, val in enumerate(row):
            c = cells[j]
            c.text = ""
            par = c.paragraphs[0]
            par.paragraph_format.space_after = Pt(0)
            par.paragraph_format.line_spacing = 1.0
            txt = "" if val is None else str(val)
            if i >= len(hdrs) and j == 0 and (i - len(hdrs)) in indent_rows:
                par.paragraph_format.left_indent = Cm(0.35)
            run = par.add_run(txt)
            run.font.size = Pt(font)
            run.font.name = "Times New Roman"
            pPr = par._p.get_or_add_pPr()
            mrk = OxmlElement("w:rPr")
            sz = OxmlElement("w:sz")
            sz.set(qn("w:val"), str(int(font * 2)))
            mrk.append(sz)
            pPr.append(mrk)
            if i < len(hdrs) or (i - len(hdrs)) in bold_rows:
                run.bold = (i < len(hdrs)) or True
            if i < len(hdrs) and txt == "":
                pass
            par.alignment = WD_ALIGN_PARAGRAPH.LEFT if j == 0 else WD_ALIGN_PARAGRAPH.CENTER
            set_cell_border(c, top=NONE, bottom=NONE, left=NONE, right=NONE)
    for c in t.rows[0].cells:
        set_cell_border(c, top=LINE)
    for c in t.rows[len(hdrs) - 1].cells:
        set_cell_border(c, bottom=THIN)
    for c in t.rows[-1].cells:
        set_cell_border(c, bottom=LINE)
    if header2:  # merge spanning header cells with identical text
        row = t.rows[0]
        j = 0
        while j < len(header2):
            k = j
            while k + 1 < len(header2) and header2[k + 1] == header2[j] and header2[j]:
                k += 1
            if k > j:
                m = row.cells[j].merge(row.cells[k])
                m.text = ""
                pr = m.paragraphs[0]
                rr = pr.add_run(header2[j])
                rr.bold = True
                rr.font.size = Pt(font)
                pr.alignment = WD_ALIGN_PARAGRAPH.CENTER
                set_cell_border(m, top=LINE, bottom=THIN)
            j = k + 1
    if widths:
        scale = TABLE_W / sum(widths)
        widths = [w * scale for w in widths]
        tblPr = t._tbl.tblPr
        lay = OxmlElement("w:tblLayout")
        lay.set(qn("w:type"), "fixed")
        tblPr.append(lay)
        tw = OxmlElement("w:tblW")
        tw.set(qn("w:w"), str(int(sum(widths) / 2.54 * 1440)))
        tw.set(qn("w:type"), "dxa")
        old = tblPr.find(qn("w:tblW"))
        if old is not None:
            tblPr.remove(old)
        tblPr.append(tw)
        grid = t._tbl.tblGrid
        for j, gc in enumerate(grid.findall(qn("w:gridCol"))):
            gc.set(qn("w:w"), str(int(widths[j] / 2.54 * 1440)))
        for row in t.rows:
            for j, w in enumerate(widths):
                if j < len(row.cells):
                    row.cells[j].width = Cm(w)
    p = doc.add_paragraph()
    r = p.add_run("Note. ")
    r.italic = True
    r.font.size = Pt(9)
    for chunk, b, i in parse(note):
        rr = p.add_run(chunk)
        rr.font.size = Pt(9)
        rr.bold = b
        rr.italic = i
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.space_after = Pt(14)


def figure(num, title, path, caption, width=16):
    p = doc.add_paragraph()
    r = p.add_run(f"Figure {num}")
    r.bold = True
    if num != 1:
        p.paragraph_format.page_break_before = True
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.line_spacing = 1.0
    p = doc.add_paragraph()
    r = p.add_run(title)
    r.italic = True
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.line_spacing = 1.15
    doc.add_picture(path, width=Cm(width))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.paragraphs[-1].paragraph_format.keep_with_next = True
    p = doc.add_paragraph()
    r = p.add_run("Note. ")
    r.italic = True
    r.font.size = Pt(9)
    for chunk, b, i in parse(caption):
        rr = p.add_run(chunk)
        rr.font.size = Pt(9)
        rr.bold = b
        rr.italic = i
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.space_after = Pt(14)


def page_break():
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


# ------------------------------------------------------------------ pull numbers
cov = {c["measure"]: c for c in R["coverage"]}
prim = R["coverage"][0]
elig = R["coverage"][1]
surv = R["coverage"][2]
swal = R["coverage"][3]
obs = R["coverage"][4]
A_, B_ = R["modelA"], R["modelB"]
mc = R["modelC"].set_index("term")
mb = R["modelB_table"].set_index("term")
mci = R["modelC_mi"].set_index("term")
ml = R["multilevel"]
eq = R["equity"]
em = R["em"]
emp = R["em_pd"]
c80 = R["comm_80"]
casc = R["cascade"].set_index("round")
rs = R["reasons"]
rn = R["reasons_n"]
n = R["n_by_round"]
RV = R["rev"]
SC = RV["survey_cov"]

# ================================================================== TITLE
p = doc.add_paragraph()
r = p.add_run(
    "Treatment uptake and its correlates across three rounds of ivermectin and moxidectin mass drug administration for onchocerciasis in Twifo Atti-Morkwa, Ghana: repeated cross-sectional surveys"
)
r.bold = True
r.font.size = Pt(14)
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
P("Paper 3 — Results report: statistical methods, results, tables and figures", italic=True).alignment = (
    WD_ALIGN_PARAGRAPH.CENTER
)
P(
    "Prepared 3 November 2026. Analysis dataset: paper3_uptake (1,200 respondents; three independent post-MDA cross-sectional surveys). Analyses follow the prespecified Paper 3 analysis plan; deviations are listed at the end of the Methods. Acceptability, satisfaction and treatment-experience data are excluded by design.",
    size=10,
)

# ================================================================== METHODS (statistical analysis)
H("Statistical analysis", 1)
P(
    "The three post-MDA surveys were analysed as independent cross-sectional samples; respondents were not linked across rounds, and round was treated as a between-sample variable. The primary outcome was self-reported receipt of onchocerciasis medicine at the index MDA among respondents who recalled that distribution (n=1,091). Secondary outcomes were eligible coverage (respondents reporting that they were ineligible removed from the denominator), survey coverage (all 1,200 respondents, non-recall counted as not received), swallowing of all tablets among recipients, directly observed swallowing (Round 3 only) and reasons for non-receipt."
)
P(
    "Proportions are reported with 95% CIs that account for clustering of respondents within the 22 communities (ratio estimator, logit scale, *t* distribution with *G*−1 degrees of freedom). Community-level receipt is reported with exact Clopper–Pearson intervals. Differences in sample composition between rounds are summarised with standardised mean differences (SMD), multi-category for categorical variables; SMDs above 0·10 indicate meaningful imbalance."
)
P(
    "Receipt was modelled with modified Poisson regression (log link). Variance was estimated with the CR2 (Bell–McCaffrey) cluster-robust estimator on 22 communities, with inference on a *t* distribution with 21 degrees of freedom. Model A included round only. Model B added prespecified antecedent characteristics (age group, sex, education, household wealth quintile, farming household, permanent residence, residence for under 12 of the past 12 months and functional disability [Washington Group short set]) and sub-district fixed effects. Round contrasts are reported as standardised receipt (marginal standardisation to the pooled analytic sample), adjusted prevalence differences (PD, percentage points) and adjusted prevalence ratios (aPR), with delta-method CIs. As a check, CIs were also obtained by cluster bootstrap (999 replicates, communities resampled within sub-districts). Because round and drug are fully confounded, round contrasts describe differences between implementation rounds and are not interpreted as drug effects. The Round 3 versus Round 2 contrast compares two moxidectin rounds."
)
P(
    "Model C extended Model B with round-trip time to the river and with information and knowledge variables (health information from radio, health workers, community drug distributors and community information centres; knowledge score; personal concern about onchocerciasis; perceived presence of black flies). These were measured after the MDA and are reported as correlates rather than determinants. All variables were prespecified; no data-driven selection was used. Variance inflation factors were below 3."
)
P(
    "Effect modification by round was assessed for age (14–24, 25–44, ≥45 years), sex, wealth (quintiles 1–2, 3, 4–5) and permanent residence using product terms, joint Wald *F* tests and standardised receipt within each subgroup. Associations were interpreted only where every round-by-subgroup cell contained at least ten non-recipients; otherwise they are presented descriptively. Socioeconomic inequality in receipt was summarised within each round by the slope index of inequality (SII, linear model) and relative index of inequality (RII, log-Poisson model) on the within-round wealth-index ridit. Between-community variation was estimated with random-intercept logistic models (adaptive quadrature, 40 nodes) and summarised as the intraclass correlation (ICC, latent scale) and median odds ratio (MOR)."
)
P(
    "Sensitivity analyses comprised: lower and upper bounds for respondents who did not recall the MDA; inverse probability of recall weighting; eligible coverage as the outcome; restriction to the 19 communities sampled in all three rounds; interviewer fixed effects; logistic regression with marginal standardisation; multiple imputation of missing covariates (20 imputations, chained equations, Rubin’s rules); and E-values for unmeasured confounding. Analyses used Python 3 (statsmodels 0.15) with custom CR2, standardisation and quadrature routines. Reporting follows STROBE for cross-sectional studies."
)
P(
    "**Deviations from the analysis plan.** Model C has 33 parameters for 230 non-recipients (about seven events per parameter, above the prespecified 20–24 degrees of freedom); estimates for modified Poisson models remain stable at this level, and multiple-imputation estimates were concordant (Supplementary Table S1). Interaction models used three age and three wealth groups rather than six age groups and five quintiles, because the prespecified cell-size rule could not be met with finer categories. Between-community variation is summarised with the median odds ratio from logistic models rather than the median rate ratio. The cluster bootstrap replaced the wild cluster bootstrap."
)

# ================================================================== RESULTS
H("Results", 1)
H("Participants", 2)
P(
    f'Of 1,200 respondents surveyed (400 per round), 1,091 (90·9%) recalled the index MDA and formed the analytic sample: {n[1]} in Round 1 (ivermectin), {n[2]} in Round 2 and {n[3]} in Round 3 (both moxidectin). Recall was lower in Round 1 ({pc(casc.loc[1,"recalled"]/400)}%) and Round 3 ({pc(casc.loc[3,"recalled"]/400)}%) than in Round 2 ({pc(casc.loc[2,"recalled"]/400)}%), and lower among young people aged 14–24 years ({pc(RV['recall_age'][True][0]/RV['recall_age'][True][1])}%) than among adults ({pc(RV['recall_age'][False][0]/RV['recall_age'][False][1])}%). [FILL: number of households approached, eligible residents absent at the time of the survey, and refusals, by round, for the flow diagram]. Respondents were predominantly female (61·7%) and from farming households (80·1%); 90·4% were permanent residents (table 1). The three samples differed modestly in composition. Round 3 had fewer respondents in the least-poor wealth quintile and more living over 30 minutes from the river (SMD versus Round 1 0·33 and 0·25). Rounds 2 and 3 had fewer respondents with primary education only (SMD 0·29 and 0·23). Rounds 2 and 3 also more often reported radio as a source of health information (SMD 0·28 and 0·27) and less often reported black flies in their community (SMD 0·32 for both), supporting adjustment before comparing rounds. Perceived black-fly presence was probably lower in Rounds 2 and 3 because those surveys took place in the dry season.'
)

H("Treatment receipt and the treatment cascade", 2)
P(
    f'Two outcomes are reported throughout. Survey coverage, which counts every respondent and treats those who did not recall the MDA as untreated, was {pc(surv[1]["p"])}% ({ci(surv[1]["lo"], surv[1]["hi"], 1, 100)}), {pc(surv[2]["p"])}% ({ci(surv[2]["lo"], surv[2]["hi"], 1, 100)}) and {pc(surv[3]["p"])}% ({ci(surv[3]["lo"], surv[3]["hi"], 1, 100)}) in Rounds 1–3, and was below 80% in every round. Reported receipt among respondents who recalled the MDA was {pc(prim[1]["p"])}% (95% CI {ci(prim[1]["lo"], prim[1]["hi"], 1, 100)}) in Round 1, {pc(prim[2]["p"])}% ({ci(prim[2]["lo"], prim[2]["hi"], 1, 100)}) in Round 2 and {pc(prim[3]["p"])}% ({ci(prim[3]["lo"], prim[3]["hi"], 1, 100)}) in Round 3 (table 2). With self-reported ineligible respondents excluded, eligible coverage was {pc(elig[1]["p"])}%, {pc(elig[2]["p"])}% and {pc(elig[3]["p"])}%; these figures refer to respondents aged 14 years or older and are not directly comparable with the WHO target of 80% therapeutic coverage of the total population, which includes children. Design effects for the primary proportion were {f(RV['deff'][1]['deff'],1)}, {f(RV['deff'][2]['deff'],1)} and {f(RV['deff'][3]['deff'],1)} (effective sample sizes {RV['deff'][1]['n_eff']:.0f}, {RV['deff'][2]['n_eff']:.0f} and {RV['deff'][3]['n_eff']:.0f}). Once tablets were received, almost all were swallowed (≥98·8% in every round). In Round 3, {pc(obs[3]["p"])}% ({ci(obs[3]["lo"], obs[3]["hi"], 1, 100)}) of those who swallowed all tablets reported swallowing in front of the distributor. The largest loss along the cascade therefore occurred between recalling the MDA and receiving treatment, not after receipt (figure 1).'
)

H("Differences between rounds", 2)
P(
    f'After standardisation for antecedent characteristics and sub-district, receipt was {pc(B_["cov_R1"][0])}% in Round 1, {pc(B_["cov_R2"][0])}% in Round 2 and {pc(B_["cov_R3"][0])}% in Round 3 (table 3). Compared with the ivermectin round, receipt was {f(100*B_["PD_R2_R1"][0])} percentage points higher in Round 2 (95% CI {ci(B_["PD_R2_R1"][1], B_["PD_R2_R1"][2], 1, 100)}; aPR {est(B_["PR_R2_R1"])}) and {f(100*B_["PD_R3_R1"][0])} points higher in Round 3 ({ci(B_["PD_R3_R1"][1], B_["PD_R3_R1"][2], 1, 100)}; aPR {est(B_["PR_R3_R1"])}). Receipt did not differ between the two moxidectin rounds (PD {f(100*B_["PD_R3_R2"][0])} points, {ci(B_["PD_R3_R2"][1], B_["PD_R3_R2"][2], 1, 100)}). Adjustment changed the crude contrasts little. Intervals use Bell–McCaffrey (Satterthwaite) degrees of freedom (about {B_['df']['PD_R2_R1']:.0f} for these contrasts); a cluster bootstrap gave intervals about 20% narrower and is not used for inference because it is anti-conservative with this number of clusters. For survey coverage, the corresponding differences were {f(100*SC['PD_R2_R1'][0])} percentage points (Round 2 vs Round 1; {ci(SC['PD_R2_R1'][1], SC['PD_R2_R1'][2], 1, 100)}) and {f(100*SC['PD_R3_R1'][0])} points (Round 3 vs Round 1; {ci(SC['PD_R3_R1'][1], SC['PD_R3_R1'][2], 1, 100)}). Replacing sub-district with community fixed effects gave {f(100*S['community_fe']['PD_R2_R1'][0])} and {f(100*S['community_fe']['PD_R3_R1'][0])} points (table 8). Because medicine, calendar time, mobilisation and sampling all changed together between rounds, these contrasts describe higher reported receipt during the moxidectin rounds and are not estimates of a drug effect.'
)

H("Reasons for non-receipt", 2)
r_ = rs.set_index("reason")
P(
    f'Of the 240 non-recipients, the most common reason was absence from home at the time of distribution ({r_.loc["Not at home","all"][0]}; {f(r_.loc["Not at home","all"][1])}%), followed by refusal ({r_.loc["Refused","all"][0]}; {f(r_.loc["Refused","all"][1])}%) and self-reported ineligibility ({r_.loc["Not eligible","all"][0]}; {f(r_.loc["Not eligible","all"][1])}%); only {r_.loc["Distributor never came","all"][0]} ({f(r_.loc["Distributor never came","all"][1])}%) reported that the distributor never came (table 4). The distribution of all five reasons differed across rounds (χ²={f(RV['reasons_full']['chi2'],1)}, df={RV['reasons_full']['df']}, Monte Carlo p={pv(RV['reasons_full']['p_mc'])}). The share of non-recipients reporting ineligibility rose from {f(r_.loc["Not eligible",1][1])}% in Round 1 to {f(r_.loc["Not eligible",3][1])}% in Round 3, while refusal remained between {f(r_.loc["Refused",3][1])}% and {f(r_.loc["Refused",1][1])}%. Of the {RV['not_eligible']['n']} respondents who reported being ineligible, {RV['not_eligible']['female']} were women and {RV['not_eligible']['female_15_49']} were women aged 15–49 years, consistent with exclusion during pregnancy or breastfeeding; the questionnaire did not record the specific reason. [FILL: report any information on refusal reasons from the free-text field].'
)

H("Variation between communities", 2)
P(
    f'Community-level receipt ranged widely within every round (figure 2). Excluding one community with only two respondents in Round 1, the number of communities at or above 80% receipt was {RV['comm_80_n5'][1][0]} of {RV['comm_80_n5'][1][1]} in Round 1, {RV['comm_80_n5'][2][0]} of {RV['comm_80_n5'][2][1]} in Round 2 and {RV['comm_80_n5'][3][0]} of {RV['comm_80_n5'][3][1]} in Round 3; community estimates are imprecise because each rested on about 20 respondents. Between-community heterogeneity was greatest in Round 3: the ICC was {f(ml[(1,"null")]["ICC"],2)} in Round 1, {f(ml[(2,"null")]["ICC"],2)} in Round 2 and {f(ml[(3,"null")]["ICC"],2)} in Round 3, corresponding to median odds ratios of {f(ml[(1,"null")]["MOR"],2)}, {f(ml[(2,"null")]["MOR"],2)} and {f(ml[(3,"null")]["MOR"],2)} (table 7). Heterogeneity remained after adjustment for individual characteristics (Round 3 MOR {f(ml[(3,"adj")]["MOR"],2)}); in Round 1 the adjusted MOR ({f(ml[(1,"adj")]["MOR"],2)}) exceeded the unadjusted value ({f(ml[(1,"null")]["MOR"],2)}), indicating that individual characteristics masked rather than explained some between-community variation. On the probability scale, the intraclass correlation was {f(RV['icc_obs'][1],2)}, {f(RV['icc_obs'][2],2)} and {f(RV['icc_obs'][3],2)}. Three communities (C11, C12 and C13) were below 80% in all three rounds, and {len(RV['persistent_low'])} communities were below 80% in at least two rounds. Because community estimates are based on about 20 respondents, some apparent persistence may reflect chance, and other communities that were low in Round 1 were above 80% in Round 2.'
)

H("Factors associated with receipt", 2)
P(
    f'Round contrasts are taken from Model B; Model C, which adds variables measured after distribution, describes correlates of receipt and its round coefficients are not interpreted. In the pooled multivariable model (Model C; n={R["modelC_n"]:,}), receipt was higher among respondents aged 55–64 years (aPR {est((mc.loc["age_grp=5","est"], mc.loc["age_grp=5","lo"], mc.loc["age_grp=5","hi"]))}) and 65 years or older ({est((mc.loc["age_grp=6","est"], mc.loc["age_grp=6","lo"], mc.loc["age_grp=6","hi"]))}) than among those aged 14–24 years. It was also higher among members of farming households ({est((mc.loc["farming_hh","est"], mc.loc["farming_hh","lo"], mc.loc["farming_hh","hi"]))}) and permanent residents ({est((mc.loc["permanent_res","est"], mc.loc["permanent_res","lo"], mc.loc["permanent_res","hi"]))}) (table 5; figure 4). Receipt was lower in the Morkwa sub-district than in the reference sub-district (aPR {est((mc.loc["subdistrict=2","est"], mc.loc["subdistrict=2","lo"], mc.loc["subdistrict=2","hi"]))}). Receipt was not associated with sex, education, household wealth, functional disability, recent residence or time to the river. None of the information sources, the knowledge score, concern about onchocerciasis or perceived black-fly presence was independently associated with receipt, and all their CIs included 1. Estimates were concordant after multiple imputation of missing covariates (Supplementary Table S1). Model C has more parameters than there are clusters, so joint tests of large blocks of coefficients are not reported. Crude receipt ranged from {pc(RV['interviewer_range'][0])}% to {pc(RV['interviewer_range'][1])}% across the six interviewers.'
)

H("Differences by subgroup across rounds", 2)
y1, y2, y3 = emp["age3"][1][0][0], emp["age3"][1][1][0], emp["age3"][1][2][0]
o1, o2, o3 = emp["age3"][3][0][0], emp["age3"][3][1][0], emp["age3"][3][2][0]
P(
    f'Young people aged 14–24 years had the lowest standardised receipt in Round 1 ({pc(y1)}%, 95% CI {ci(emp["age3"][1][0][1], emp["age3"][1][0][2], 1, 100)}), {f(100*(o1-y1))} percentage points below those aged 45 years or older ({pc(o1)}%). Receipt among young people was {pc(y2)}% in Round 2 and {pc(y3)}% in Round 3 (figure 3; table 6). The difference between rounds was therefore largest in the youngest age group (Round 2 versus Round 1: {f(100*emp["age3"][1][4][0])} points, {ci(emp["age3"][1][4][1], emp["age3"][1][4][2], 1, 100)}) and smallest among those aged 45 years or older ({f(100*emp["age3"][3][4][0])} points). The prespecified age-by-round interaction (three age groups by three rounds) was not statistically significant (p={pv(em["age3"]["wald"][2])}), and one cell had fewer than ten non-recipients, so this pattern is descriptive. A similar descriptive pattern was seen for non-permanent residents, whose standardised receipt was {pc(emp["permanent_res"][0][0][0])}% in Round 1 and {pc(emp["permanent_res"][0][1][0])}% and {pc(emp["permanent_res"][0][2][0])}% in Rounds 2 and 3 (interaction p={pv(em["permanent_res"]["wald"][2])}). Differences between rounds did not vary by sex (p={pv(em["female"]["wald"][2])}) or wealth (p={pv(em["ses3"]["wald"][2])}).'
)

H("Socioeconomic equity", 2)
P(
    f'Estimates of the socioeconomic gradient were imprecise. There was no clear gradient in Round 1 (SII {f(100*eq[1]["SII"][0])} percentage points, 95% CI {ci(eq[1]["SII"][1], eq[1]["SII"][2], 1, 100)}) or Round 2 ({f(100*eq[2]["SII"][0])}, {ci(eq[2]["SII"][1], eq[2]["SII"][2], 1, 100)}). In Round 3, receipt tended to be lower among less-poor households (SII {f(100*eq[3]["SII"][0])}, {ci(eq[3]["SII"][1], eq[3]["SII"][2], 1, 100)}; RII {est(eq[3]["RII"])}), but CIs included no gradient, and the change in gradient across rounds was not significant (F on {RV['sii_change_df'][0]} and {RV['sii_change_df'][1]} df, p={pv(eq["change_wald"][2])}; table 7). The CIs are compatible with moderate gradients in either direction, so these data neither show nor exclude socioeconomic inequality.'
)

H("Sensitivity analyses", 2)
lo_pd = min(
    S[k]["PD_R2_R1"][0]
    for k in [
        "main",
        "bound_lower",
        "bound_upper",
        "ipw",
        "eligible",
        "comm19",
        "interviewer",
        "logistic",
        "mi",
        "community_fe",
    ]
)
hi_pd = max(
    S[k]["PD_R2_R1"][0]
    for k in [
        "main",
        "bound_lower",
        "bound_upper",
        "ipw",
        "eligible",
        "comm19",
        "interviewer",
        "logistic",
        "mi",
        "community_fe",
    ]
)
lo3 = min(
    S[k]["PD_R3_R1"][0]
    for k in [
        "main",
        "bound_lower",
        "bound_upper",
        "ipw",
        "eligible",
        "comm19",
        "interviewer",
        "logistic",
        "mi",
        "community_fe",
    ]
)
hi3 = max(
    S[k]["PD_R3_R1"][0]
    for k in [
        "main",
        "bound_lower",
        "bound_upper",
        "ipw",
        "eligible",
        "comm19",
        "interviewer",
        "logistic",
        "mi",
        "community_fe",
    ]
)
P(
    f'The direction and approximate size of the round contrasts were consistent across all sensitivity analyses (table 8). The Round 2 versus Round 1 difference ranged from {f(100*lo_pd)} to {f(100*hi_pd)} percentage points and the Round 3 versus Round 1 difference from {f(100*lo3)} to {f(100*hi3)} points, with every CI excluding zero. The extreme assumptions about non-recall had the largest influence. Treating all non-recallers as untreated widened the Round 2 advantage to {f(100*S["bound_lower"]["PD_R2_R1"][0])} points, and treating them all as treated narrowed it to {f(100*S["bound_upper"]["PD_R2_R1"][0])} points. Weighting for the probability of recall, restricting to communities sampled in every round, adding interviewer or community fixed effects, logistic modelling and multiple imputation each changed the contrasts by less than three percentage points. In a tipping-point analysis (figure S1), the Round 2 versus Round 1 difference kept a CI above zero unless at least 90% of Round 1 non-recallers were assumed to have participated and far fewer of those in Rounds 2–3 (20% or less when Round 1 was set at 90%; 60% or less at 100%). The Round 3 versus Round 1 difference was more fragile: its CI included zero once Round 1 non-recallers were assumed to have participated about 20–30 percentage points more often than those in Rounds 2–3. With equal assumptions in all rounds, both differences stayed above zero for any assumed participation from 0% to 100%. These analyses address measured differences between samples; they cannot address changes in implementation between rounds, so E-values for unmeasured confounding are not reported. The two moxidectin rounds did not differ in any analysis.'
)

H("Interpretation (for the Discussion)", 2)
P(
    "Across three post-MDA surveys, reported receipt was about 11–13 percentage points higher during the two moxidectin rounds than during the preceding ivermectin round. The difference persisted after accounting for differences in sample composition and was stable across analytic assumptions; it did not grow or shrink between the first and second moxidectin rounds. Losses occurred mostly before treatment was offered, mainly through absence from home at distribution, rather than through refusal or incomplete swallowing. Three features of who was missed stand out. Young people and non-permanent residents had the lowest receipt during the ivermectin round, and the higher receipt in later rounds was most marked in these groups. Receipt was concentrated geographically, with the same communities and the Morkwa sub-district repeatedly below the 80% threshold. And receipt showed no socioeconomic gradient favouring wealthier households. None of these patterns can be attributed to moxidectin itself: drug, calendar time, mobilisation intensity and sampling changed together between rounds, information and knowledge were measured after distribution, and receipt was self-reported."
)

# ================================================================== TABLES
new_section(True)
H("Tables", 1)
P(
    "Proposed placement (Lancet limit of five display items in the main text): tables 1, 2 and 5 and figures 1 and 2 in the main text; the remaining tables and figures in the appendix.",
    size=10,
    italic=True,
)

# Table 1
t1 = R["table1"]
rows, bold, ind = [], [], []
for _, r in t1.iterrows():
    if r["var"]:
        multi = (t1.loc[t1["var"] == r["var"]].shape[0] > 1) if False else None
    rows.append(
        [
            r["var"] if r["var"] else "",
            r["level"],
            r["R1"],
            r["R2"],
            r["R3"],
            r["R0"],
            "" if pd.isna(r["SMD21"]) else f(r["SMD21"], 2),
            "" if pd.isna(r["SMD31"]) else f(r["SMD31"], 2),
        ]
    )
hdr = [
    "Characteristic",
    "Category",
    f"Round 1 IVM (n={n[1]})",
    f"Round 2 MOX (n={n[2]})",
    f"Round 3 MOX (n={n[3]})",
    f"Total (n={sum(n.values()):,})",
    "SMD R2 vs R1",
    "SMD R3 vs R1",
]
rows = [[x.replace(".", "·") if i in (2, 3, 4, 5) else x for i, x in enumerate(rw)] for rw in rows]
apa_table(
    1,
    "Characteristics of Respondents Who Recalled the Index Mass Drug Administration, by Round",
    hdr,
    rows,
    'Values are *n* (%) unless otherwise indicated; percentages use non-missing values. For binary characteristics only the "yes" category is shown. SMD = standardised mean difference (multi-category for categorical variables; values >0·10 indicate meaningful imbalance). IVM = ivermectin; MOX = moxidectin; JHS = junior high school; WG-SS = Washington Group Short Set (any domain "a lot of difficulty"); CDD = community drug distributor. Household wealth quintiles are derived from a principal component asset index computed on the pooled sample. Knowledge score (0–3) = heard of onchocerciasis + identifies flies as the route of transmission + recognises that infection can be asymptomatic. Information, knowledge, concern and black-fly items were recorded after the MDA.',
    widths=[3.6, 2.6, 1.9, 1.9, 1.9, 1.9, 1.3, 1.3],
    font=8,
)


# Table 2
def cp(c):
    return f'{c["k"]}/{c["n"]}', f'{pc(c["p"])} ({ci(c["lo"], c["hi"], 1, 100)})'


rows = []
for c, lab in [
    (surv, "Survey coverage (co-primary)ᶜ"),
    (prim, "Reported receipt among recallers (co-primary)ᵃ"),
    (elig, "Eligible coverageᵇ"),
    (swal, "Swallowed all tablets, among recipients"),
]:
    rr = [lab]
    for k in (1, 2, 3, "all"):
        a, b = cp(c[k])
        rr += [a, b]
    rows.append(rr)
a, b = cp(obs[3])
rows.append(
    [
        "Swallowed in front of distributor, among those who swallowed all tabletsᵈ",
        "–",
        "–",
        "–",
        "–",
        a,
        b,
        "–",
        "–",
    ]
)
c8 = R["rev"]["comm_80_n5"]
rows.append(
    [
        "Communities with receipt among recallers ≥80%, n/Nᵉ",
        "",
        f"{c8[1][0]}/{c8[1][1]}",
        "",
        f"{c8[2][0]}/{c8[2][1]}",
        "",
        f"{c8[3][0]}/{c8[3][1]}",
        "",
        "–",
    ]
)
h2 = [
    "",
    "Round 1 · ivermectin",
    "Round 1 · ivermectin",
    "Round 2 · moxidectin",
    "Round 2 · moxidectin",
    "Round 3 · moxidectin",
    "Round 3 · moxidectin",
    "All rounds",
    "All rounds",
]
hdr = ["Measure", "n/N", "% (95% CI)", "n/N", "% (95% CI)", "n/N", "% (95% CI)", "n/N", "% (95% CI)"]
apa_table(
    2,
    "Reported Treatment Receipt, Coverage and Swallowing by Round",
    hdr,
    rows,
    f'CIs account for clustering within communities (ratio estimator, logit scale, *t* with G−1 df, where G is the number of communities in that round: 21, 20 and 20). Design effects for receipt among recallers: {f(R["rev"]["deff"][1]["deff"],1)}, {f(R["rev"]["deff"][2]["deff"],1)} and {f(R["rev"]["deff"][3]["deff"],1)}. ᵃAmong respondents who recalled the index MDA. ᵇAs (a), excluding respondents who reported being ineligible for treatment (Round 1 *n*=10, Round 2 *n*=9, Round 3 *n*=19). ᶜAll surveyed respondents; those who did not recall the MDA are counted as not treated (lower bound). ᵈAsked in Round 3 only; denominator is those who swallowed all tablets. ᵉCommunities with at least five respondents. Respondents were aged 14 years or older; the WHO target of 80% therapeutic coverage refers to the total population, including children, so these survey estimates are not directly comparable with it. Survey-based receipt is self-reported and is not equivalent to programme-reported coverage.',
    widths=[4.4, 1.3, 2.1, 1.3, 2.1, 1.3, 2.1, 1.4, 2.1],
    font=8,
    header2=h2,
)


# Table 3
def row3(lab, key, scale=100, d=1):
    out = [lab]
    for m in (A_, B_):
        e = m[key]
        out.append(f"{f(e[0]*scale, d)} ({ci(e[1], e[2], d, scale)})")
    e = SC[key]
    out.append(f"{f(e[0]*scale, d)} ({ci(e[1], e[2], d, scale)})")
    pval = B_[key][3] if len(B_[key]) > 3 else np.nan
    out.append(pv(pval) if not np.isnan(pval) else "")
    return out


rows = [["Standardised receipt, %", "", "", "", ""]]
rows += [
    row3("Round 1 · ivermectin", "cov_R1"),
    row3("Round 2 · moxidectin", "cov_R2"),
    row3("Round 3 · moxidectin", "cov_R3"),
]
rows += [["Prevalence difference, percentage points", "", "", "", ""]]
rows += [
    row3("Round 2 vs Round 1", "PD_R2_R1"),
    row3("Round 3 vs Round 1", "PD_R3_R1"),
    row3("Round 3 vs Round 2", "PD_R3_R2"),
]
rows += [["Prevalence ratio", "", "", "", ""]]
rows += [
    row3("Round 2 vs Round 1", "PR_R2_R1", 1, 2),
    row3("Round 3 vs Round 1", "PR_R3_R1", 1, 2),
    row3("Round 3 vs Round 2", "PR_R3_R2", 1, 2),
]
hdr = [
    "Contrast",
    f'Receipt among recallers, Model A: crude (n={R["modelA_n"]:,})',
    f'Receipt among recallers, Model B: standardised (n={R["modelB_n"]:,})',
    "Survey coverage, Model B: standardised (n=1,178)",
    "p (Model B, recallers)",
]
apa_table(
    3,
    "Crude and Standardised Differences in Reported Treatment Receipt Between Rounds",
    hdr,
    rows,
    f'Modified Poisson regression with CR2 cluster-robust variance (22 communities) and Bell–McCaffrey (Satterthwaite) degrees of freedom (about {B_["df"]["PD_R2_R1"]:.0f} for the round contrasts). Survey coverage counts all respondents, with those who did not recall the MDA as not treated. Model B is adjusted for age group, sex, education, household wealth quintile, farming household, permanent residence, residence <12 of the past 12 months, functional disability and sub-district. Standardised receipt is the mean predicted probability with every respondent assigned to each round in turn (marginal standardisation to the pooled analytic sample). A cluster bootstrap (999 replicates, communities resampled within sub-districts) gave intervals about 20% narrower, for example {ci(R["modelB_boot"]["PD_R2_R1"][0], R["modelB_boot"]["PD_R2_R1"][1], 1, 100)} for Round 2 vs Round 1, and is not used for inference because it is anti-conservative with few clusters. Round and drug are fully confounded; contrasts describe implementation rounds, not drug effects.',
    widths=[4.6, 3.3, 3.3, 3.3, 1.8],
    bold_rows=(0, 4, 8),
    indent_rows=(1, 2, 3, 5, 6, 7, 9, 10, 11),
    font=8.5,
)

# Table 4
rows = []
for _, r in rs.iterrows():
    rows.append([r.reason, r.side] + [f"{r[k][0]} ({f(r[k][1])})" for k in (1, 2, 3, "all")])
side = R["reasons_test"]["table"]
rows.append(
    [
        "Programme-side reasons, total",
        "",
        f'{side[1]["prog"]} ({f(100*side[1]["prog"]/rn[1])})',
        f'{side[2]["prog"]} ({f(100*side[2]["prog"]/rn[2])})',
        f'{side[3]["prog"]} ({f(100*side[3]["prog"]/rn[3])})',
        f'{side[1]["prog"]+side[2]["prog"]+side[3]["prog"]} ({f(100*(side[1]["prog"]+side[2]["prog"]+side[3]["prog"])/240)})',
    ]
)
rows.append(
    [
        "Person-side reasons, total",
        "",
        f'{side[1]["person"]} ({f(100*side[1]["person"]/rn[1])})',
        f'{side[2]["person"]} ({f(100*side[2]["person"]/rn[2])})',
        f'{side[3]["person"]} ({f(100*side[3]["person"]/rn[3])})',
        f'{side[1]["person"]+side[2]["person"]+side[3]["person"]} ({f(100*(side[1]["person"]+side[2]["person"]+side[3]["person"])/240)})',
    ]
)
hdr = [
    "Reason",
    "Classification",
    f"Round 1 IVM (n={rn[1]})",
    f"Round 2 MOX (n={rn[2]})",
    f"Round 3 MOX (n={rn[3]})",
    "Total (n=240)",
]
apa_table(
    4,
    "Reported Reasons for Not Receiving Treatment Among Non-Recipients, by Round",
    hdr,
    rows,
    f'Values are *n* (%) of non-recipients who recalled the MDA. Programme-side = not at home at the time of distribution or distributor never came; person-side = refused or reported being ineligible. Distribution of the five reasons across rounds: χ²={f(R["rev"]["reasons_full"]["chi2"],1)}, df={R["rev"]["reasons_full"]["df"]}, Monte Carlo p={pv(R["rev"]["reasons_full"]["p_mc"])} (10,000 permutations). Of the {R["rev"]["not_eligible"]["n"]} respondents reporting ineligibility, {R["rev"]["not_eligible"]["female_15_49"]} were women aged 15–49 years. "Other" responses mostly described illness or pregnancy. Free-text reasons for refusal were available for Rounds 2–3 only.',
    widths=[4.2, 2.8, 2.4, 2.4, 2.4, 2.4],
    bold_rows=(5, 6),
    font=8.5,
)

# Table 5
order = [
    ("Age group, years (ref: 14–24)", "age_grp", 1),
    ("25–34", "age_grp", 2),
    ("35–44", "age_grp", 3),
    ("45–54", "age_grp", 4),
    ("55–64", "age_grp", 5),
    ("≥65", "age_grp", 6),
    ("Sex (ref: male)", "female", 0),
    ("Female", "female", 1),
    ("Education (ref: none)", "educ4", 0),
    ("Primary", "educ4", 1),
    ("JHS/middle", "educ4", 2),
    ("Secondary or higher", "educ4", 3),
    ("Household wealth quintile (ref: Q1, poorest)", "ses_q", 1),
    ("Q2", "ses_q", 2),
    ("Q3", "ses_q", 3),
    ("Q4", "ses_q", 4),
    ("Q5 (least poor)", "ses_q", 5),
    ("Farming household (ref: no)", "farming_hh", 0),
    ("Yes", "farming_hh", 1),
    ("Permanent resident (ref: no)", "permanent_res", 0),
    ("Yes", "permanent_res", 1),
    ("Lived in community <12 of past 12 months (ref: no)", "months_lt12", 0),
    ("Yes", "months_lt12", 1),
    ("Functional disability (ref: no)", "wg_disability", 0),
    ("Yes", "wg_disability", 1),
    ("Round-trip time to river (ref: ≤10 min)", "river_dist_grp", 1),
    ("11–30 min", "river_dist_grp", 2),
    ("31–60 min", "river_dist_grp", 3),
    (">60 min", "river_dist_grp", 4),
    ("Information and knowledge (measured after MDA)ᵃ", None, None),
    ("Health information from radio", "info_radio", 1),
    ("Health information from health worker", "info_healthworker", 1),
    ("Health information from CDD/volunteer", "info_cdd", 1),
    ("Health information from community information centre", "info_cic", 1),
    ("Knowledge score, per point (0–3)", "knowledge_score", "cont"),
    ("Personally concerned about onchocerciasis", "concern_yes", 1),
    ("Black flies perceived present", "blackflies_yes", 1),
]
rows, bold, ind = [], [], []
lv = R["levels"]
un = R["unadj"]
cn = {1: "R1", 2: "R2", 3: "R3"}
for i, (lab, v, code) in enumerate(order):
    if v is None:
        rows.append([lab, "", "", "", ""])
        bold.append(i)
        continue
    if v == "round":
        name = f"round={code}"
        k_ = R["coverage"][0][code]
        rec = f'{k_["k"]}/{k_["n"]} ({pc(k_["p"])})'
        u = A_[f"PR_R{code}_R1"]
        rows.append(
            [
                lab,
                rec,
                est(u),
                est((mc.loc[name, "est"], mc.loc[name, "lo"], mc.loc[name, "hi"])),
                pv(mc.loc[name, "p"]),
            ]
        )
        ind.append(i)
        continue
    if code == "cont":
        tb = un[v]
        uu = tb.iloc[0]
        rows.append(
            [
                lab,
                "—",
                est((uu.est, uu.lo, uu.hi)),
                est((mc.loc[v, "est"], mc.loc[v, "lo"], mc.loc[v, "hi"])),
                pv(mc.loc[v, "p"]),
            ]
        )
        ind.append(i)
        continue
    L = lv[v].get(float(code)) or lv[v].get(code)
    rec = f'{int(L["sum"])}/{int(L["size"])} ({pc(L["sum"]/L["size"])})' if L else ""
    binary = v in (
        "female",
        "farming_hh",
        "permanent_res",
        "months_lt12",
        "wg_disability",
        "info_radio",
        "info_healthworker",
        "info_cdd",
        "info_cic",
        "concern_yes",
        "blackflies_yes",
    )
    name = v if binary else f"{v}={code}"
    is_ref = (binary and code == 0) or (
        not binary and code == {"age_grp": 1, "educ4": 0, "ses_q": 1, "river_dist_grp": 1}[v]
    )
    if is_ref:
        rows.append([lab, rec, "1 (ref)", "1 (ref)", ""])
        bold.append(i) if False else None
        continue
    tb = un[v].set_index("term")
    uu = tb.loc[name]
    rows.append(
        [
            lab,
            rec,
            est((uu.est, uu.lo, uu.hi)),
            est((mc.loc[name, "est"], mc.loc[name, "lo"], mc.loc[name, "hi"])),
            pv(mc.loc[name, "p"]),
        ]
    )
    ind.append(i)
g = R["modelC_global"]
hdr = [
    "Characteristic",
    "Received, n/N (%)",
    "Round-adjusted PR (95% CI)",
    "Adjusted PR (95% CI), Model C",
    "p",
]
apa_table(
    5,
    "Characteristics Associated With Reported Treatment Receipt, Pooled Across Rounds",
    hdr,
    rows,
    f'Modified Poisson regression with CR2 cluster-robust variance (22 communities). Round-adjusted PR: each characteristic entered with round only. Model C (*n*={R["modelC_n"]:,}; {R["modelC_events"]} non-recipients; {R["modelC_k"]} parameters) includes all characteristics shown plus sub-district fixed effects (Morkwa vs Bimpong Egya aPR {f(mc.loc["subdistrict=2","est"],2)}, {ci(mc.loc["subdistrict=2","lo"], mc.loc["subdistrict=2","hi"],2)}). Model C also includes round; its round coefficients are not shown because round contrasts are estimated from Model B (table 3). Because Model C has more parameters than clusters, joint tests of multi-category variables are not reported. CIs use Bell–McCaffrey degrees of freedom. For binary information and knowledge items, the reference is "no". ᵃThese characteristics were measured after distribution and may reflect contact with the programme; associations are not interpreted as determinants. PR = prevalence ratio; CDD = community drug distributor; JHS = junior high school.',
    widths=[5.8, 2.8, 3.2, 3.4, 1.3],
    bold_rows=tuple(bold),
    indent_rows=tuple(ind),
    font=8,
)

# Table 6
rows, bold, ind = [], [], []
groups = [
    ("age3", "Age group", {1: "14–24 years", 2: "25–44 years", 3: "≥45 years"}),
    ("female", "Sex", {0: "Male", 1: "Female"}),
    (
        "ses3",
        "Household wealth",
        {1: "Quintiles 1–2 (poorer)", 2: "Quintile 3", 3: "Quintiles 4–5 (less poor)"},
    ),
    ("permanent_res", "Residence", {0: "Not permanent", 1: "Permanent"}),
]
cells = R["em_cells"]
for v, lab, lvls in groups:
    W = em[v]["wald"]
    flag = "" if em[v]["min_cell"] >= 10 else "ᵃ"
    rows.append([f"{lab} (interaction p={pv(W[2])}){flag}", "", "", "", "", ""])
    bold.append(len(rows) - 1)
    for code, name in lvls.items():
        e = emp[v][code]
        rows.append(
            [
                name,
                f"{pc(e[0][0])} ({ci(e[0][1], e[0][2], 1, 100)})",
                f"{pc(e[1][0])} ({ci(e[1][1], e[1][2], 1, 100)})",
                f"{pc(e[2][0])} ({ci(e[2][1], e[2][2], 1, 100)})",
                f"{f(100*e[4][0])} ({ci(e[4][1], e[4][2], 1, 100)})",
                f"{f(100*e[3][0])} ({ci(e[3][1], e[3][2], 1, 100)})",
            ]
        )
        ind.append(len(rows) - 1)
hdr = [
    "Subgroup",
    "Round 1 · IVM, %",
    "Round 2 · MOX, %",
    "Round 3 · MOX, %",
    "R2 − R1, points",
    "R3 − R1, points",
]
apa_table(
    6,
    "Standardised Reported Treatment Receipt by Round Within Population Subgroups",
    hdr,
    rows,
    "Values are standardised receipt or prevalence differences (95% CI) from Model B with a round-by-subgroup product term (modified Poisson, CR2 variance, *t*₂₁), standardised to the pooled analytic sample. Interaction *p* values are joint Wald *F* tests of the product terms. ᵃAt least one round-by-subgroup cell had fewer than ten non-recipients (age 14–24 in Round 2, *n*=8; non-permanent residents in Round 3, *n*=7); the pattern is reported descriptively. IVM = ivermectin; MOX = moxidectin.",
    widths=[4.4, 2.6, 2.6, 2.6, 2.6, 2.6],
    bold_rows=tuple(bold),
    indent_rows=tuple(ind),
    font=8,
)

# Table 7
rows = [
    ["Between-community variation", "", "", ""],
    ["Variance of community intercept (null)"] + [f(ml[(k, "null")]["var"], 2) for k in (1, 2, 3)],
    ["ICC, latent scale (null)"] + [f(ml[(k, "null")]["ICC"], 2) for k in (1, 2, 3)],
    ["Median odds ratio (null)"] + [f(ml[(k, "null")]["MOR"], 2) for k in (1, 2, 3)],
    ["Median odds ratio (adjusted)ᵃ"] + [f(ml[(k, "adj")]["MOR"], 2) for k in (1, 2, 3)],
    ["Communities with receipt ≥80%, n/N"] + [f"{c80[k][0]}/{c80[k][1]}" for k in (1, 2, 3)],
    ["Socioeconomic inequality (household wealth)", "", "", ""],
    ["Slope index of inequality, percentage points (95% CI)"]
    + [f'{f(100*eq[k]["SII"][0])} ({ci(eq[k]["SII"][1], eq[k]["SII"][2], 1, 100)})' for k in (1, 2, 3)],
    ["Relative index of inequality (95% CI)"] + [est(eq[k]["RII"]) for k in (1, 2, 3)],
    ["Age inequality", "", "", ""],
    ["Crude receipt gap, ≥45 vs 14–24 years, percentage points"]
    + [f(100 * eq[f"agegap_{k}"][0]) for k in (1, 2, 3)],
]
hdr = ["Measure", "Round 1 · ivermectin", "Round 2 · moxidectin", "Round 3 · moxidectin"]
apa_table(
    7,
    "Between-Community Variation and Inequality in Reported Treatment Receipt, by Round",
    hdr,
    rows,
    f'Random-intercept logistic models fitted separately by round (adaptive Gauss–Hermite quadrature, 40 nodes). ICC = intraclass correlation on the latent scale, σ²/(σ²+π²/3). Median odds ratio = exp(√(2σ²)·Φ⁻¹[0·75]), the median odds ratio between two randomly chosen communities. ᵃAdjusted for the Model B individual characteristics. The slope index (linear model) and relative index (log-Poisson model) of inequality compare the least poor with the poorest end of the within-round wealth-index ridit; negative values indicate higher receipt among poorer households. Change in the slope index across rounds: *F*={f(eq["change_wald"][0],2)}, *p*={pv(eq["change_wald"][2])}.',
    widths=[7.2, 3.3, 3.3, 3.3],
    bold_rows=(0, 6, 9),
    indent_rows=(1, 2, 3, 4, 5, 7, 8, 10),
    font=8.5,
)

# Table 8
labels = [
    ("main", "Main analysis (Model B)"),
    ("bound_lower", "Non-recall counted as not received (lower bound)ᵃ"),
    ("bound_upper", "Non-recall counted as received (upper bound)ᵃ"),
    ("ipw", "Inverse probability of recall weightingᵇ"),
    ("eligible", "Eligible respondents only"),
    ("comm19", "Communities sampled in all three rounds (n=19)"),
    ("interviewer", "Interviewer fixed effects"),
    ("logistic", "Logistic regression, marginal standardisation"),
    ("mi", "Multiple imputation of covariates (m=20)"),
    ("community_fe", "Community fixed effects instead of sub-district"),
]
rows = []
for k, lab in labels:
    e = S[k]
    rows.append(
        [lab]
        + [pc(e[c][0]) for c in ("cov_R1", "cov_R2", "cov_R3")]
        + [f"{f(100*e[c][0])} ({ci(e[c][1], e[c][2], 1, 100)})" for c in ("PD_R2_R1", "PD_R3_R1", "PD_R3_R2")]
    )
hdr = [
    "Analysis",
    "R1, %",
    "R2, %",
    "R3, %",
    "R2 − R1, points (95% CI)",
    "R3 − R1, points (95% CI)",
    "R3 − R2, points (95% CI)",
]
apa_table(
    8,
    "Sensitivity Analyses for Standardised Differences in Reported Treatment Receipt Between Rounds",
    hdr,
    rows,
    f'All analyses use the Model B adjustment set and marginal standardisation with CR2 cluster-robust CIs and Bell–McCaffrey degrees of freedom (multiple-imputation row: *t*₂₁). ᵃAll 1,200 respondents; the 109 who did not recall the MDA are assigned not received (lower bound) or received (upper bound). ᵇWeights are the inverse of the predicted probability of recalling the MDA from round, Model B characteristics and time to river (weights {f(S["ipw_wt_range"][0],2)}–{f(S["ipw_wt_range"][1],2)}). Multiple-imputation estimates combined with Rubin’s rules. R = round.',
    widths=[5.6, 1.3, 1.3, 1.3, 2.9, 2.9, 2.9],
    font=8,
)

# Supplementary Table S1: Model C CC vs MI
rows = []
lab = {
    "round=2": "Round 2 · moxidectin",
    "round=3": "Round 3 · moxidectin",
    "age_grp=2": "Age 25–34",
    "age_grp=3": "Age 35–44",
    "age_grp=4": "Age 45–54",
    "age_grp=5": "Age 55–64",
    "age_grp=6": "Age ≥65",
    "female": "Female",
    "educ4=1": "Primary education",
    "educ4=2": "JHS/middle",
    "educ4=3": "Secondary or higher",
    "ses_q=2": "Wealth Q2",
    "ses_q=3": "Wealth Q3",
    "ses_q=4": "Wealth Q4",
    "ses_q=5": "Wealth Q5",
    "farming_hh": "Farming household",
    "permanent_res": "Permanent resident",
    "months_lt12": "Lived <12 months in community",
    "wg_disability": "Functional disability",
    "river_dist_grp=2": "River 11–30 min",
    "river_dist_grp=3": "River 31–60 min",
    "river_dist_grp=4": "River >60 min",
    "info_radio": "Radio",
    "info_healthworker": "Health worker",
    "info_cdd": "CDD/volunteer",
    "info_cic": "Community information centre",
    "knowledge_score": "Knowledge score (per point)",
    "concern_yes": "Concerned about onchocerciasis",
    "blackflies_yes": "Black flies perceived present",
}
for t, L in lab.items():
    rows.append(
        [
            L,
            est((mc.loc[t, "est"], mc.loc[t, "lo"], mc.loc[t, "hi"])),
            est((mci.loc[t, "est"], mci.loc[t, "lo"], mci.loc[t, "hi"])),
        ]
    )
apa_table(
    "S1",
    "Model C Adjusted Prevalence Ratios: Complete-Case Versus Multiple-Imputation Estimates",
    ["Characteristic", f'Complete case (n={R["modelC_n"]:,})', "Multiple imputation (n=1,091)"],
    rows,
    "Reference categories as in Table 5. Multiple imputation by chained equations (20 imputations), pooled with Rubin’s rules; CR2 cluster-robust within-imputation variance. Sub-district fixed effects included but not shown.",
    widths=[6.5, 4.5, 4.5],
    font=8.5,
)

# ================================================================== FIGURES
new_section(False)
H("Figures", 1)
figure(
    1,
    "Treatment Cascade From Survey Enumeration to Swallowing of All Tablets, by Mass Drug Administration Round",
    f"{FIG}/Figure1_treatment_cascade.png",
    "Each line follows one round’s survey sample (400 respondents per round) through successive steps: recalling the index MDA, reporting receipt of treatment and reporting swallowing all tablets offered. Values are percentages of all surveyed respondents, so the final step is equivalent to survey coverage for complete treatment; end labels give the final value. The grey horizontal line marks 80% for reference; respondents were aged 14 years or older, so the final step is not directly comparable with the WHO target of 80% therapeutic coverage of the total population. Recall is conditional on being at home for the interview. The steepest decline in every round occurred between recall and receipt, while losses after receipt were negligible (≥98·8% of recipients swallowed all tablets). Samples are independent across rounds; lines connect stages within a round and do not represent the same individuals over time. MDA = mass drug administration.",
    width=16,
)
figure(
    2,
    "Reported Treatment Receipt by Community and Round",
    f"{FIG}/Figure2_community_receipt.png",
    'Points show the proportion of respondents in each community who reported receiving treatment, among those recalling the index MDA; horizontal lines are exact (Clopper–Pearson) 95% CIs. Communities are identified by code (key held by the district health directorate) and appear in code order in all three panels, so each community can be followed across rounds. Orange marks communities below 80% (vertical grey line); grey marks communities at or above it. "Not sampled" indicates communities not surveyed in that round. Communities contribute about 20 respondents per round, so individual estimates are imprecise; the hollow point marks a community with two respondents in Round 1, which is excluded from the community counts. Three communities were below 80% in all three rounds.',
    width=16.5,
)
figure(
    3,
    "Standardised Reported Treatment Receipt by Age Group and Round",
    f"{FIG}/Figure3_receipt_by_age_round.png",
    "Points are standardised receipt (marginal standardisation to the pooled analytic sample) from a modified Poisson model including a round-by-age product term and adjusted for sex, education, wealth quintile, farming household, permanent residence, recent residence, functional disability and sub-district; vertical lines are 95% CIs from CR2 cluster-robust variance (22 communities). Colours identify rounds (blue = Round 1, ivermectin; orange = Round 2, moxidectin; aqua = Round 3, moxidectin). The grey horizontal line marks 80%. Young people aged 14–24 years had the lowest receipt during the ivermectin round, and the difference between rounds was largest in this group; the age-by-round interaction was not statistically significant (p=0·07) and one cell contained fewer than ten non-recipients, so the pattern is descriptive.",
    width=15,
)
figure(
    4,
    "Adjusted Prevalence Ratios for Reported Treatment Receipt, Pooled Across Rounds (Model C)",
    f"{FIG}/Figure4_forest_modelC.png",
    f'Squares are adjusted prevalence ratios and horizontal lines are 95% CIs from a modified Poisson model with CR2 cluster-robust variance (*n*={R["modelC_n"]:,}; 22 communities), mutually adjusted for all characteristics shown and for sub-district. The x-axis is logarithmic so that ratios above and below 1 are displayed symmetrically; the vertical line at 1 indicates no association. Blue marks antecedent characteristics and green marks information and knowledge items, which were measured after distribution and are shown as correlates only. Round was included in the model but its coefficients are not shown; round contrasts are estimated from Model B (table 3). CIs use Bell–McCaffrey degrees of freedom.',
    width=15.5,
)

figure(
    "S1",
    "Tipping-Point Analysis for Respondents Who Did Not Recall the Mass Drug Administration",
    f"{FIG}/FigureS1_tipping_point.png",
    "Each cell shows the standardised difference in participation (percentage points; Model B, Bell–McCaffrey CIs) between the stated moxidectin round and the ivermectin round when non-recallers (54, 17 and 38 respondents in Rounds 1–3) are assigned the stated probability of having participated, separately for Round 1 (x-axis) and Rounds 2–3 (y-axis). Hatched cells: 95% CI includes zero. Dashed line: the same assumption in all rounds. The bottom-left cell is survey coverage (all non-recallers counted as not participating).",
    width=16,
)
doc.save(OUTF)
print("saved", OUTF)
