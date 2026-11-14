"""Build analysis-ready datasets for Papers 3 (uptake), 5 (spatial) and 6 (youth)
from Phase I_Final Survey data_labels.xlsx, guided by the manuscript variable audit.

Usage: python3 -I build.py <survey.xlsx> <audit.xlsx> <outdir>
"""
import sys, re, math
import numpy as np, pandas as pd, openpyxl, pyreadstat, warnings
warnings.filterwarnings('ignore')

SURVEY, AUDIT, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
DK = 98  # code for "Don't know" style responses, retained as a distinct category

# Read with literal "None"/"NA" kept as responses (pandas treats them as missing by default)
raw = pd.read_excel(SURVEY, header=0, keep_default_na=False, na_values=[''])
assert raw.shape == (1200, 208), raw.shape
LAB = {i + 1: re.sub(r'\s+', ' ', str(c).replace('\xa0', ' ')).strip() for i, c in enumerate(raw.columns)}

def col(i):
    s = raw.iloc[:, i - 1]
    return s.map(lambda x: re.sub(r'\s+', ' ', x.replace('\xa0', ' ')).strip() if isinstance(x, str) else x)

D = pd.DataFrame(index=raw.index)
META = {}      # var -> dict(label, src, values, notes)
FLAGS = []     # data-cleaning log rows

def reg(var, label, src=None, values=None, notes=''):
    META[var] = dict(label=label, src=src, values=values or {}, notes=notes)

def log(var, rows, issue, action):
    rows = list(rows)
    if rows:
        FLAGS.append(dict(variable=var, n_records=len(rows),
                          record_uids=', '.join(D.loc[rows, 'resp_uid'].astype(str).tolist()[:40]) + (' …' if len(rows) > 40 else ''),
                          issue=issue, action=action))

def mapcat(var, src, mapping, label=None, notes='', other_ok=False):
    s = col(src)
    vals = {}
    out = pd.Series(np.nan, index=raw.index)
    for k, v in mapping.items():
        out[s == k] = v
        vals.setdefault(v, k)
    un = s[s.notna() & ~s.isin(mapping.keys())]
    if len(un) and not other_ok:
        raise ValueError(f"{var} (col {src}) unmapped values: {un.value_counts().to_dict()}")
    D[var] = out
    reg(var, label or LAB[src], src, {int(k): v for k, v in sorted(vals.items())}, notes)

def checkbox(var, src, label=None, notes=''):
    mapcat(var, src, {'Unchecked': 0, 'Checked': 1}, label, notes)

def numclean(var, src, label, lo, hi, fixes=None, notes=''):
    s = col(src)
    fixes = fixes or {}
    out = []
    for i, x in s.items():
        if isinstance(x, str) and x in fixes:
            out.append(fixes[x])
        else:
            try:
                out.append(float(x))
            except (TypeError, ValueError):
                out.append(np.nan)
    out = pd.Series(out, index=raw.index, dtype=float)
    bad_text = s.notna() & out.isna()
    log(var, s.index[bad_text], f"non-numeric entries: {sorted(set(map(str, s[bad_text])))}", 'set to missing')
    fixed = s.isin(list(fixes.keys()))
    log(var, s.index[fixed], f"text entries recoded: { {k: v for k, v in fixes.items() if (s == k).any()} }", 'recoded as shown')
    oor = out.notna() & ~out.between(lo, hi)
    log(var, s.index[oor], f"implausible values outside {lo}–{hi}: {sorted(out[oor].tolist())}", 'set to missing')
    out[oor] = np.nan
    D[var] = out
    reg(var, label, src, None, notes)

# ---------------------------------------------------------------- design
D['record_id'] = col(1).astype(int)
ph = col(2)
D['round'] = ph.map({'Post Ivermectin MDA': 1, 'Post Moxidectin MDA 1': 2, 'Post Moxidectin MDA 2': 3})
D['resp_uid'] = 'R' + D['round'].astype(int).astype(str) + '_' + D['record_id'].map('{:03d}'.format)
assert D['resp_uid'].is_unique
reg('resp_uid', 'Unique respondent key (round + Record ID)', None, None,
    'Record ID repeats across rounds but does NOT identify the same person (sex agrees in only ~56% and community in ~17% of ID pairs between Rounds 1 and 2). Treat rounds as independent cross-sections.')
reg('record_id', 'Record ID (within round)', 1)
reg('round', 'Study phase / MDA round', 2, {1: 'Post Ivermectin MDA (Round 1)', 2: 'Post Moxidectin MDA 1 (Round 2)', 3: 'Post Moxidectin MDA 2 (Round 3)'})
D['drug_moxi'] = (D['round'] > 1).astype(int)
reg('drug_moxi', 'Drug of index MDA', 2, {0: 'Ivermectin', 1: 'Moxidectin'}, 'Fully confounded with round: drug effect cannot be separated from time/implementation.')

sd = col(10).str.replace(' Sub-District', '', regex=False)
sd_codes = {k: i + 1 for i, k in enumerate(sorted(sd.unique()))}
D['subdistrict'] = sd.map(sd_codes)
reg('subdistrict', 'Sub-district', 10, {v: k for k, v in sd_codes.items()})
cm = col(11)
cm_codes = {k: i + 1 for i, k in enumerate(sorted(cm.unique()))}
D['community'] = cm.map(cm_codes)
reg('community', 'Community (cluster)', 11, {v: k for k, v in cm_codes.items()},
    'Use as cluster in models. Not all communities sampled every round (e.g. C09 and C21 Round 1–2 only; C17 Rounds 2–3; C20 only 4 in Round 1).')
D['community_name'] = cm
reg('community_name', 'Community name (text)', 11)

iv = col(8).str.replace('Jnr', 'Jr.', regex=False)
log('interviewer', raw.index[col(8).str.contains('Jnr', na=False)], "'Mr. Isaac Toffey Jnr' and 'Mr. Isaac Toffey Jr.' are one interviewer", 'harmonised')
iv_codes = {k: i + 1 for i, k in enumerate(sorted(iv.unique()))}
D['interviewer'] = iv.map(iv_codes)
reg('interviewer', 'Interviewer', 8, {v: k for k, v in iv_codes.items()}, 'Names harmonised; consider as a random effect / fixed effect for interviewer variance.')
mapcat('interviewer_sex', 9, {'Male': 0, 'Female': 1}, 'Sex of interviewer')

dt = pd.to_datetime(col(7).astype(str), errors='coerce', format='mixed')
D['interview_date'] = dt.dt.normalize()
reg('interview_date', 'Date of interview', 7, None, 'Round 1 stored as Excel datetimes, Rounds 2–3 as text; harmonised.')
assert D['interview_date'].notna().all()

# GPS ---------------------------------------------------------------
lon_raw, lat_raw = col(5), col(6)
lon = pd.to_numeric(lon_raw, errors='coerce'); lat = pd.to_numeric(lat_raw, errors='coerce')
gflag = pd.Series(0, index=raw.index)
typo = lon_raw.astype(str).str.contains('h', na=False)
lon[typo] = pd.to_numeric(lon_raw[typo].astype(str).str.replace('h', '', regex=False))
gflag[typo] = 3; log('gps_lon', raw.index[typo], "stray character in longitude", "character removed; within community range")
swap = (lon > 0) & (lat < 0)
lon[swap], lat[swap] = lat[swap].values, lon[swap].values
gflag[swap] = 1; log('gps_lon/gps_lat', raw.index[swap], 'latitude and longitude entered in swapped fields', 'swapped back')
dec = lon.abs() > 1000
lon[dec] = lon[dec] / 1e6
gflag[dec] = 2; log('gps_lon', raw.index[dec], 'decimal point missing in longitude (e.g. -1601805)', 'divided by 1,000,000; result lies within the community range')
box = lon.between(-1.9, -1.3) & lat.between(5.4, 6.0)
bad = (lon.notna() | lat.notna()) & ~box
log('gps_lon/gps_lat', raw.index[bad], 'coordinates outside study area or only one coordinate recorded', 'both set to missing')
lon[~box] = np.nan; lat[~box] = np.nan
gflag[bad] = 4
# distance from community median
med = pd.DataFrame({'lon': lon, 'lat': lat, 'c': cm}).groupby('c')[['lon', 'lat']].transform('median')
dist_km = np.sqrt(((lon - med['lon']) * 111.32 * np.cos(np.radians(5.65))) ** 2 + ((lat - med['lat']) * 110.57) ** 2)
far = dist_km > 5
gflag[far & (gflag == 0)] = 5
log('gps_lon/gps_lat', raw.index[far], 'point lies >5 km from its community median location', 'kept, flagged (gps_flag=5) for checking')
D['gps_lon'], D['gps_lat'], D['gps_flag'] = lon, lat, gflag
D['gps_km_from_comm_median'] = dist_km.round(2)
reg('gps_lon', 'GPS longitude (cleaned)', 5, None, 'CONFIDENTIAL: household-level location. Do not publish; aggregate to community for maps.')
reg('gps_lat', 'GPS latitude (cleaned)', 6, None, 'CONFIDENTIAL: household-level location. Do not publish; aggregate to community for maps.')
reg('gps_flag', 'GPS cleaning flag', '5–6', {0: 'Recorded as entered', 1: 'Lat/long swapped – corrected', 2: 'Missing decimal – corrected', 3: 'Typo removed', 4: 'Invalid/incomplete – set missing', 5: '>5 km from community median – check'})
reg('gps_km_from_comm_median', 'Distance (km) from community median GPS point', '5–6', None, 'Derived. Useful for spotting mis-assigned points.')

# ---------------------------------------------------------------- demographics
numclean('age', 12, 'Age (years)', 14, 100)
D['age_grp'] = pd.cut(D['age'], [13, 24, 34, 44, 54, 64, 200], labels=[1, 2, 3, 4, 5, 6]).astype(float)
reg('age_grp', 'Age group', 12, {1: '14–24', 2: '25–34', 3: '35–44', 4: '45–54', 5: '55–64', 6: '65+'})
D['youth_14_24'] = D['age'].between(14, 24).astype(float); D.loc[D['age'].isna(), 'youth_14_24'] = np.nan
reg('youth_14_24', 'Young person aged 14–24', 12, {0: 'No (25+)', 1: 'Yes (14–24)'}, 'Paper 6 population.')
mapcat('female', 13, {'Male': 0, 'Female': 1}, 'Sex of respondent')
mapcat('educ', 14, {'No school at all': 0, 'Completed some primary school': 1, 'Completed primary school': 2,
                    'Completed JHS/middle school': 3, 'Completed secondary school': 4, 'Completed college/university': 5},
       'Highest education completed (ordinal)')
D['educ4'] = D['educ'].map({0: 0, 1: 1, 2: 1, 3: 2, 4: 3, 5: 3})
reg('educ4', 'Education (4 groups)', 14, {0: 'None', 1: 'Primary (some/completed)', 2: 'JHS/middle', 3: 'Secondary or higher'}, 'Derived from educ.')
mapcat('health_today', 15, {'Poor': 1, 'Fair': 2, 'Neutral': 3, 'Good': 4, 'Excellent': 5}, 'Self-rated health today')
D['health_good'] = (D['health_today'] >= 4).astype(float)
reg('health_good', 'Self-rated health good/excellent', 15, {0: 'Poor/fair/neutral', 1: 'Good/excellent'}, 'Derived.')
YN = {'No': 0, 'Yes': 1}; YNDK = {'No': 0, 'Yes': 1, "Don't know": DK, "I don't know": DK}
mapcat('other_meds', 16, YNDK, 'Took medication for other illness in last year')

# SES / household
mapcat('income_source', 155, {'Farming': 1, 'Small scale enterprise': 2, 'Daily labourer': 3, 'Private employment': 4,
                              'Government/civil servant': 5, 'Mining': 6, 'Other?': 7}, 'Primary source of household income')
D['farming_hh'] = (D['income_source'] == 1).astype(float)
reg('farming_hh', 'Farming is main household income', 155, {0: 'No', 1: 'Yes'}, 'Derived.')
mapcat('income_fixed', 156, YNDK, 'Household income fixed each month')
numclean('income_month', 157, 'Average monthly household income (GHS)', 1, 100000,
         notes="Self-reported, heavily skewed: use log or quintiles. 'Less than 40 cedis', '4t0', 'No response', 'No comment', \"She doesn't know\" set missing.")
D['income_q'] = pd.qcut(D['income_month'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5]).astype(float)
reg('income_q', 'Monthly household income quintile (pooled sample)', 157, {1: 'Q1 lowest', 2: 'Q2', 3: 'Q3', 4: 'Q4', 5: 'Q5 highest'}, 'Derived; ties broken by row order.')
mapcat('permanent_res', 158, YN, 'Lives in this community permanently')
numclean('months_in_comm', 159, 'Months lived in community, last 12 months', 0, 12, fixes={'2 weeks': 0.5, '11 month': 11},
         notes='Values >12 (13, 20, 100, 120, 200, 400) are impossible for a 12-month recall and set missing.')
numclean('river_dist_min', 160, 'Round-trip time to river (minutes)', 0, 360,
         notes="'No' (x4), 'Q0', '30p' set missing. Self-reported proxy, not entomological exposure.")
D['river_dist_grp'] = pd.cut(D['river_dist_min'], [-1, 10, 30, 60, 1000], labels=[1, 2, 3, 4]).astype(float)
reg('river_dist_grp', 'Round-trip time to river (groups)', 160, {1: '≤10 min', 2: '11–30 min', 3: '31–60 min', 4: '>60 min'}, 'Derived.')

assets = {163: 'electricity', 164: 'radio', 165: 'television', 166: 'landline_phone', 167: 'computer', 168: 'refrigerator',
          169: 'freezer', 170: 'generator', 171: 'washing_machine', 172: 'camera', 173: 'video_player', 174: 'sewing_machine',
          175: 'bed', 176: 'table', 177: 'chair', 178: 'cabinet', 179: 'watch', 180: 'mobile_phone', 181: 'bicycle',
          182: 'motorcycle', 183: 'animal_cart', 184: 'car', 185: 'boat'}
for c, n in assets.items():
    checkbox('hh_' + n, c, f'Household owns: {LAB[c]}' if c != 166 else 'Household owns: mobile telephone (questionnaire label; likely landline)')
mapcat('toilet', 188, {'No toilet': 0, 'Pit latrine/latrine': 1, 'Manual flush/water-seal with pour': 2, 'Flush toilet': 3, 'Other': 4}, 'Household toilet type')
D['toilet_improved'] = D['toilet'].map({0: 0, 1: 0, 2: 1, 3: 1, 4: np.nan})
reg('toilet_improved', 'Flush / pour-flush toilet', 188, {0: 'No toilet or pit latrine', 1: 'Flush or pour-flush'}, "Derived; pit latrines not split by slab in questionnaire, so classed with no toilet. 'Other' set missing.")
mapcat('roof', 204, {'Thatched': 1, 'Wood': 2, 'Metal/corrugated iron': 3, 'Ceramic tile': 4, 'Concrete': 5}, 'Primary roof material')
mapcat('floor', 206, {'Mud/dirt': 1, 'Wood': 2, 'concrete': 3, 'Tile': 4, 'Other (specify)': 5}, 'Primary floor material', notes="'Other' = 'Tarazo' (terrazzo).")
D['floor_finished'] = D['floor'].map({1: 0, 2: 0, 3: 1, 4: 1, 5: 1})
reg('floor_finished', 'Finished floor (concrete/tile/terrazzo)', 206, {0: 'Earth/wood', 1: 'Finished'}, 'Derived.')

# SES index: first principal component of standardised binary indicators (Filmer–Pritchett style)
ses_items = ['hh_' + n for n in assets.values() if n not in ('animal_cart', 'boat', 'landline_phone')] + ['toilet_improved', 'floor_finished']
X = D[ses_items].copy()
X = X.fillna(X.mean())
Z = (X - X.mean()) / X.std(ddof=0)
Z = Z.loc[:, Z.std() > 0]
w, v = np.linalg.eigh(np.cov(Z.T.values))
pc1 = v[:, -1]
if pc1[list(Z.columns).index('hh_refrigerator')] < 0:
    pc1 = -pc1
score = Z.values @ pc1
D['ses_index'] = (score - score.mean()) / score.std()
D['ses_q'] = pd.qcut(D['ses_index'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5]).astype(float)
var_expl = w[-1] / w.sum()
SES_LOADINGS = pd.DataFrame({'item': Z.columns, 'pc1_weight': pc1.round(3)}).sort_values('pc1_weight', ascending=False)
reg('ses_index', 'Household wealth index (PCA, standardised)', '163–185, 188, 206', None,
    f'First principal component of {Z.shape[1]} binary asset/housing indicators, pooled across rounds; explains {var_expl:.1%} of variance. Animal cart, boat and col-166 phone excluded (n<10 or ambiguous). Weights in the "SES index" sheet.')
reg('ses_q', 'Household wealth quintile', '163–185, 188, 206', {1: 'Q1 poorest', 2: 'Q2', 3: 'Q3', 4: 'Q4', 5: 'Q5 least poor'}, 'Derived from ses_index (pooled).')

# Washington Group short set
WG = {'No, no difficulty': 0, 'Yes, some difficulty': 1, 'Yes, a lot of difficulty': 2}
for c, n in {195: 'seeing', 196: 'hearing', 197: 'walking', 198: 'cognition', 199: 'selfcare', 200: 'communication'}.items():
    mapcat('wg_' + n, c, WG, f'Difficulty {n} (Washington Group)')
wgs = D[[k for k in D if k.startswith('wg_')]]
D['wg_disability'] = (wgs >= 2).any(axis=1).astype(float)
reg('wg_disability', 'Disability (WG-SS: ≥1 domain "a lot of difficulty")', '195–200', {0: 'No', 1: 'Yes'},
    'Derived. WG-SS also has a "cannot do at all" category that this questionnaire did not include.')
D['wg_any_difficulty'] = (wgs >= 1).any(axis=1).astype(float)
reg('wg_any_difficulty', 'Any functional difficulty (≥1 domain some/a lot)', '195–200', {0: 'No', 1: 'Yes'}, 'Derived.')

# ---------------------------------------------------------------- knowledge & perceptions
mapcat('heard_oncho', 17, YN)
mapcat('oncho_understanding', 18, {'No knowledge': 1, 'A little': 2, 'Average': 3, 'Good': 4, 'Very Good': 5, "Don't know": DK},
       'Self-rated understanding of onchocerciasis', notes='Asked if heard_oncho = Yes.')
for c, n in {20: 'worms', 21: 'flies', 22: 'water', 23: 'curse', 24: 'hereditary', 25: 'other', 26: 'dk'}.items():
    checkbox('transmit_' + n, c, f'Transmission belief: {LAB[c]}', 'Checkbox: 0 also for respondents never asked (heard_oncho=No); restrict to heard_oncho=1 where needed.')
mapcat('oncho_asymptomatic', 28, {'No': 0, 'Yes': 1, 'Maybe': 2, "Don't know": DK}, notes='Nominal: Maybe and DK kept distinct.')
mapcat('most_exposed', 29, {'Everyone': 1, 'Men': 2, 'Women': 3, 'Boys': 4, 'Girls': 5, 'Other (specify)': 6, "Don't know": DK})
mapcat('comm_prevalence', 31, {'None': 0, 'Few': 1, 'Some': 2, 'Quite a lot': 3, 'Many': 4, "Don't know": DK},
       'Perceived number in community with onchocerciasis',
       notes="'None' is a valid response (729 respondents); default spreadsheet import reads it as blank.")
CONC = {'No, not at all': 1, 'Not really': 2, 'Maybe': 3, 'Yes, a bit': 4, 'Yes, definitely': 5, "Don't know": DK}
mapcat('concern_oncho', 32, CONC, 'Personally concerned about onchocerciasis')
mapcat('blackflies', 33, CONC, 'Black flies present in community (perceived)', notes='Asked in all rounds.')
D['blackflies_yes'] = D['blackflies'].map({1: 0, 2: 0, 3: 0, 4: 1, 5: 1})
reg('blackflies_yes', 'Black flies present (yes a bit/definitely)', 33, {0: 'No/not really/maybe', 1: 'Yes'}, "Derived; Don't know set missing.")
# knowledge score (all respondents; never-heard = 0)
k1 = D['heard_oncho']; k2 = D['transmit_flies']; k3 = (D['oncho_asymptomatic'] == 1).astype(float)
D['know_flies'] = k2; reg('know_flies', 'Knows black flies transmit onchocerciasis', 21, {0: 'No', 1: 'Yes'}, 'Same as transmit_flies; 0 for never-heard.')
D['know_asymptomatic'] = k3; reg('know_asymptomatic', 'Knows infection can be asymptomatic', 28, {0: 'No/maybe/DK/not asked', 1: 'Yes'}, 'Derived.')
D['knowledge_score'] = k1 + k2 + k3
reg('knowledge_score', 'Onchocerciasis knowledge score (0–3)', '17, 21, 28', None,
    'Derived, unweighted: heard of oncho + flies as transmission + can be infected without symptoms. Proposed only — confirm against the writing plan.')

# Round 3 only
mapcat('blackfly_season', 34, {'Wet season': 1, 'Dry season': 2, 'All year round': 3}, 'Season black flies noticed', notes='Round 3 only.')
mapcat('blackfly_time', 36, {'Morning': 1, 'Midday': 2, 'Evening': 3, 'All day': 4}, 'Time of day black flies noticed', notes='Round 3 only.')
mapcat('fast_river', 38, YN, 'Fast-flowing river in/near community', notes='Round 3 only.')
mapcat('river_dries', 39, YNDK, 'River dries up in dry season', notes='Round 3 only.')
mapcat('river_activity', 40, {'Agricultural activity': 1, 'Mining': 2, 'Sand collection': 3, 'Fishing': 4, 'Other (specify)': 5},
       'Main economic activity near/in river', notes="Round 3 only. Exported as single choice although the question says 'mark all that apply'. 'Other' text is mostly 'no work is done around the river'.")

# ---------------------------------------------------------------- MDA participation
mapcat('recall_mda', 42, YN, 'Remembers the index MDA distribution')
mapcat('received_raw', 43, YN, 'Received onchocerciasis medicine (as recorded)')
D['received'] = D['received_raw'].where(D['recall_mda'] == 1)
odd = (D['recall_mda'] == 0) & D['received_raw'].notna()
log('received', raw.index[odd], 'answered receipt question although did not recall the MDA (skip-logic breach); both answered No', 'received set missing (primary); 0 in received_itt')
reg('received', 'PRIMARY OUTCOME: received medicine, among those recalling the MDA', 43, {0: 'No', 1: 'Yes'},
    'Denominator = recall_mda = 1 (n=1,091). Missing if MDA not recalled.')
D['received_itt'] = D['received'].fillna(0)
reg('received_itt', 'Sensitivity: received medicine, non-recall counted as not received', '42–43', {0: 'No / did not recall', 1: 'Yes'},
    'Lower-bound coverage among all 1,200 respondents.')
mapcat('reason_not_received', 44, {"Wasn't home": 1, 'Refused': 2, 'Not eligible': 3, 'Distributor never came': 4, 'Other (specify)': 5},
       notes='Non-recipients only.')
D['reason_other_text'] = col(45); reg('reason_other_text', 'Other reason not received (text)', 45)
D['refusal_text'] = col(46); reg('refusal_text', 'Reason for refusal (free text)', 46, None, 'Rounds 2–3 only.')
def refusal_theme(t):
    if not isinstance(t, str): return np.nan
    t = t.lower()
    if any(w in t for w in ['afraid', 'fear', 'side effect', 'adverse', 'past experience', 'previous']): return 1
    if any(w in t for w in ['sick', 'stroke', 'stomach', 'not well', 'nursing', 'pregnan', 'old']): return 2
    if "don't have the disease" in t or 'local medicine' in t: return 3
    return 4
D['refusal_theme'] = col(46).map(refusal_theme)
reg('refusal_theme', 'Refusal reason theme (provisional keyword coding)', 46,
    {1: 'Fear of side effects / past experience', 2: 'Illness, pregnancy/nursing, old age', 3: 'Not needed / prefers local medicine', 4: 'Other / unclear'},
    'Provisional keyword coding by Claude for 30 free-text answers – check against refusal_text before use.')

mapcat('swallowed_all_raw', 47, YN, 'Swallowed all drugs offered (as recorded)')
D['swallowed_all'] = D['swallowed_all_raw'].where(D['received'] == 1)
odd = (D['received'] != 1) & D['swallowed_all_raw'].notna()
log('swallowed_all', raw.index[odd], 'swallowing question answered (No) by people who did not receive medicine', 'set missing in swallowed_all')
reg('swallowed_all', 'SECONDARY: swallowed all drugs offered (recipients only)', 47, {0: 'No', 1: 'Yes'}, 'Denominator = received = 1.')
D.drop(columns=['swallowed_all_raw'], inplace=True); META.pop('swallowed_all_raw')
D['not_swallowed_text'] = col(49); reg('not_swallowed_text', 'Why not all swallowed (text)', 49)
mapcat('swallowed_observed', 48, YN, 'Swallowed in front of distributor', notes='Round 3 recipients only.')
mapcat('satisfied', 51, YN, 'Satisfied with last distribution', notes='Ceiling effect: 849/850 yes.')
mapcat('times_taken_cat', 140, {'Never': 0, 'One time': 1, '2 or more times': 2}, 'Times taken oncho pills (incl. this year)')
numclean('times_taken_mda', 141, 'Number of times taken pills in MDA', 1, 60, notes='Value 1010 set missing.')

# ---------------------------------------------------------------- information
for c, n in {54: 'radio', 55: 'tv', 56: 'newspaper', 57: 'socialmedia', 58: 'cic', 59: 'healthworker', 60: 'cdd',
             61: 'leaders', 62: 'friends', 63: 'other'}.items():
    checkbox('info_' + n, c, f'Health information source: {LAB[c]}', 'Multi-response item (col 53 stem).')
D['n_info_sources'] = D[[k for k in D if k.startswith('info_')]].sum(axis=1)
reg('n_info_sources', 'Number of health information sources (0–10)', '54–63', None, 'Derived.')
mapcat('info_usefulness', 65, {'Not useful': 1, 'A little useful': 2, 'Neutral': 3, 'Useful': 4, 'Very useful': 5, "Don't know": DK},
       'Usefulness of pre-distribution information', notes='Recipients only (asked after receipt) – do NOT use as predictor of receipt. Placement of Neutral between "a little" and "useful" is an assumption.')
D['info_useful_bin'] = D['info_usefulness'].map({1: 0, 2: 0, 3: 0, 4: 1, 5: 1})
reg('info_useful_bin', 'Information useful/very useful', 65, {0: 'Not/a little/neutral', 1: 'Useful/very useful'}, "Derived; DK missing.")
mapcat('main_info_source', 66, {'Pill distributor': 1, 'Health influencer': 2, 'Community influencer': 3, 'Friend/family': 4,
                                'Religious leader': 5, 'Teacher': 6, 'Other (specify)': 7, "Didn't receive any information": 0},
       'Main source of onchocerciasis information')
mapcat('heard_moxi_info', 68, YN, 'Heard information about moxidectin in past 2 months', notes='Round 3 only.')
for c, n in {70: 'shirt', 71: 'poster', 72: 'brochure', 73: 'other', 74: 'none'}.items():
    checkbox('moxi_mat_' + n, c, f'Seen moxidectin material: {n}', 'Round 3 only.')
mapcat('moxi_mat_helpful', 76, {'Not helpful': 1, 'A little helpful': 2, 'Neutral': 3, 'Helpful': 4, 'Very helpful': 5},
       'Helpfulness of moxidectin material', notes='Round 3 only.')
mapcat('trust_cdd', 77, {'No trust': 1, 'Neutral': 2, 'Some trust': 3, 'A lot of trust': 4}, 'Trust in drug distribution team',
       notes='Recipients only (one non-recipient answered). Do NOT use as predictor of receipt without addressing selection.')
D['trust_high'] = D['trust_cdd'].map({1: 0, 2: 0, 3: 0, 4: 1})
reg('trust_high', 'A lot of trust in distribution team', 77, {0: 'None/neutral/some', 1: 'A lot'}, 'Derived.')

# ---------------------------------------------------------------- treatment experience (recipients)
mapcat('ate_with_pills', 78, {'No': 0, 'Yes': 1, "Can't remember": DK}, 'Ate before/shortly after pills')
mapcat('pill_taste', 88, {'No taste': 1, 'Good taste': 2, 'Bad taste': 3, "Don't know/No opinion": DK})
mapcat('pill_number', 89, {'Few pills': 1, 'Not a lot of pills': 1, 'Okay': 2, 'Several': 3, 'Many': 3, "Don't know": DK},
       'Feeling about number of pills', notes="'Few' and 'Not a lot' merged; 'Several' and 'Many' merged.")
sym = {92: 'none', 93: 'better', 94: 'nausea', 95: 'headache', 96: 'dizziness', 97: 'fever', 98: 'sleepy', 99: 'stomach_pain',
       100: 'body_pain', 101: 'swelling', 102: 'vomiting', 103: 'diarrhoea', 104: 'itchy_skin', 105: 'other'}
for c, n in sym.items():
    checkbox('sym_' + n, c, f'Day after treatment: {LAB[c]}', 'Recipients only; set missing for non-recipients (exported as "Unchecked").')
    D.loc[D['received'] != 1, 'sym_' + n] = np.nan
log('sym_*', raw.index[(D['received'] != 1)], 'symptom checkboxes stored as Unchecked for people who were not treated', 'set missing')
adv = ['sym_' + n for n in sym.values() if n not in ('none', 'better')]
D['sym_any_adverse'] = D[adv].max(axis=1)
reg('sym_any_adverse', 'Any adverse symptom the day after treatment', '94–105', {0: 'No', 1: 'Yes'}, 'Derived; recipients only.')
mapcat('ae_severity', 109, {'I had no side effects from the treatment': 0,
                            'My side effects were mild. They did not interfere with my normal daily activities, such as work or school.': 1,
                            'My side effects were moderate. They disrupted my daily activities.': 2,
                            'My side effects were severe. I was confined to bed for at least 1 day.': 3,
                            'My side effects were very severe. I had to go to the hospital.': 4},
       'Self-reported adverse-event severity', notes='Recipients only; not clinically verified.')
D['ae_any'] = (D['ae_severity'] >= 1).astype(float).where(D['ae_severity'].notna())
reg('ae_any', 'Any self-reported side effect', 109, {0: 'None', 1: 'Mild or worse'}, 'Derived.')
D['ae_mod_plus'] = (D['ae_severity'] >= 2).astype(float).where(D['ae_severity'].notna())
reg('ae_mod_plus', 'Moderate or worse side effect', 109, {0: 'None/mild', 1: 'Moderate+'}, 'Derived; only 21 events.')

FEW = {'No one': 0, 'Few': 1, 'Some': 2, 'Quite a lot': 3, 'A lot': 4, "Don't know": DK}
mapcat('know_se_others', 112, FEW, 'Number known with side effects within a week')
mapcat('family_se', 113, YNDK, 'Family member had side effects')
mapcat('concern_se', 114, CONC, 'Personally concerned about side effects')
mapcat('health_since', 115, {'Worse': 1, 'No change': 2, 'Improved': 3, 'Greatly improved': 4, "Don't know": DK}, 'Overall health since taking pills', notes='Recipients only.')
IMP = {'very unimportant for my health': 1, 'unimportant': 2, 'neutral': 3, 'important': 4, 'very important for my health': 5, "Don't know": DK}
mapcat('drug_importance', 129, IMP, 'Importance of oncho drugs for health')
mapcat('drug_safety', 130, {'Very dangerous': 1, 'Somewhat dangerous': 2, 'Neutral': 3, 'Somewhat safe': 4, 'Very safe': 5}, 'Perceived safety of drugs taken', notes='Recipients only.')
LIK = {'Disagree a lot': 1, 'Disagree': 2, 'Agree': 3, 'Agree a lot': 4}
for c, n in {131: 'lik_drugs_work', 134: 'lik_take_again', 135: 'lik_recommend', 137: 'lik_liked', 138: 'lik_good_way', 139: 'lik_help_comm'}.items():
    mapcat(n, c, LIK, notes='Asked of all who recalled MDA, incl. non-recipients.' if c != 137 else '')
    D[n + '_agree'] = (D[n] >= 3).astype(float).where(D[n].notna())
    reg(n + '_agree', LAB[c] + ' – agree/agree a lot', c, {0: 'Disagree', 1: 'Agree'}, 'Derived.')
mapcat('participation_importance', 142, {'very unimportant': 1, 'unimportant': 2, 'neutral': 3, 'important': 4, 'very important': 5, "Don't know": DK},
       'Importance of own MDA participation for community')
mapcat('take_if_not_sick', 143, YNDK, "Should take pills even if not sick")
mapcat('complete', 208, {'Incomplete': 0, 'Complete': 1}, 'Survey record complete')

# ---------------------------------------------------------------- audit lookup
wb = openpyxl.load_workbook(AUDIT, read_only=True)
def audit(sheet, ci_col, ci_cls):
    rows = list(wb[sheet].iter_rows(values_only=True))[1:]
    return {int(r[ci_col]): r[ci_cls] for r in rows if r[ci_col] is not None}
AUD = {3: audit('Paper 3 Uptake', 1, 0), 5: audit('Paper 5 Spatial', 1, 0), 6: audit('Paper 6 Youth', 1, 0)}

SRC2VARS = {}
for v, m in META.items():
    s = m['src']
    if isinstance(s, int):
        SRC2VARS.setdefault(s, []).append(v)

CORE = ['resp_uid', 'record_id', 'round', 'drug_moxi', 'subdistrict', 'community', 'community_name', 'interviewer', 'interviewer_sex',
        'interview_date', 'complete', 'age', 'age_grp', 'youth_14_24', 'female', 'educ', 'educ4', 'health_today', 'health_good',
        'income_source', 'farming_hh', 'income_month', 'income_q', 'permanent_res', 'months_in_comm', 'ses_index', 'ses_q',
        'recall_mda', 'received_raw', 'received', 'received_itt', 'reason_not_received', 'swallowed_all']
EXTRA = {
    3: ['gps_lon', 'gps_lat', 'gps_flag', 'other_meds', 'heard_oncho', 'oncho_understanding', 'transmit_flies', 'transmit_dk', 'oncho_asymptomatic', 'most_exposed',
        'comm_prevalence', 'concern_oncho', 'blackflies', 'blackflies_yes', 'know_flies', 'know_asymptomatic', 'knowledge_score',
        'reason_other_text', 'refusal_text', 'refusal_theme', 'swallowed_observed', 'not_swallowed_text', 'satisfied', 'ae_severity', 'ae_any',
        'times_taken_cat', 'times_taken_mda', 'info_radio', 'info_tv', 'info_socialmedia', 'info_cic', 'info_healthworker', 'info_cdd',
        'info_leaders', 'info_friends', 'n_info_sources', 'main_info_source', 'know_se_others', 'family_se', 'concern_se',
        'drug_importance', 'lik_drugs_work', 'lik_drugs_work_agree', 'participation_importance', 'take_if_not_sick',
        'income_fixed', 'river_dist_min', 'river_dist_grp', 'hh_electricity', 'hh_television', 'hh_refrigerator', 'hh_mobile_phone',
        'hh_motorcycle', 'toilet', 'toilet_improved', 'roof', 'floor', 'floor_finished',
        'wg_seeing', 'wg_hearing', 'wg_walking', 'wg_cognition', 'wg_selfcare', 'wg_communication', 'wg_disability', 'wg_any_difficulty',
        'info_usefulness', 'info_useful_bin', 'trust_cdd', 'trust_high', 'ate_with_pills', 'pill_taste', 'pill_number', 'drug_safety',
        'lik_take_again', 'lik_take_again_agree', 'lik_liked', 'lik_liked_agree', 'health_since'],
    5: ['gps_lon', 'gps_lat', 'gps_flag', 'gps_km_from_comm_median', 'blackflies', 'blackflies_yes', 'blackfly_season', 'blackfly_time',
        'fast_river', 'river_dries', 'river_activity', 'river_dist_min', 'river_dist_grp', 'transmit_flies', 'know_flies',
        'heard_oncho', 'oncho_understanding', 'oncho_asymptomatic', 'know_asymptomatic', 'knowledge_score', 'most_exposed',
        'comm_prevalence', 'concern_oncho', 'concern_se', 'main_info_source', 'trust_cdd', 'trust_high', 'lik_take_again', 'lik_take_again_agree',
        'ae_severity', 'ae_any', 'ae_mod_plus', 'sym_none', 'sym_nausea', 'sym_headache', 'sym_dizziness', 'sym_fever', 'sym_body_pain',
        'sym_itchy_skin', 'sym_swelling', 'sym_any_adverse', 'wg_seeing', 'wg_walking', 'wg_disability'],
    6: ['satisfied', 'lik_take_again', 'lik_take_again_agree', 'lik_recommend', 'lik_recommend_agree', 'info_usefulness', 'info_useful_bin',
        'main_info_source', 'info_radio', 'info_tv', 'info_newspaper', 'info_socialmedia', 'info_cic', 'info_healthworker', 'info_cdd',
        'info_leaders', 'info_friends', 'n_info_sources', 'trust_cdd', 'trust_high', 'heard_moxi_info', 'moxi_mat_shirt', 'moxi_mat_poster',
        'moxi_mat_brochure', 'moxi_mat_none', 'moxi_mat_helpful', 'heard_oncho', 'oncho_understanding', 'transmit_flies', 'know_flies',
        'oncho_asymptomatic', 'know_asymptomatic', 'knowledge_score', 'concern_oncho', 'blackflies', 'blackflies_yes', 'concern_se',
        'know_se_others', 'family_se', 'drug_importance', 'lik_drugs_work', 'lik_drugs_work_agree', 'lik_good_way', 'lik_good_way_agree',
        'lik_help_comm', 'lik_help_comm_agree', 'participation_importance', 'take_if_not_sick', 'times_taken_cat', 'wg_seeing', 'wg_walking',
        'wg_disability'],
}
PAPERS = {
    3: dict(slug='paper3_uptake', title='Paper 3 – MDA treatment uptake', rows=D.index,
            pop='All 1,200 respondents, Rounds 1–3 (repeated cross-sections). Primary outcome denominator: recall_mda = 1.'),
    5: dict(slug='paper5_spatial', title='Paper 5 – Spatial / black-fly exposure', rows=D.index,
            pop='All 1,200 respondents with p5_primary = 1 marking Round 3 (Post Moxidectin MDA 2), the population named in the writing plan. Black-fly season/time, river questions and moxidectin information were asked in Round 3 only.'),
    6: dict(slug='paper6_youth', title='Paper 6 – Young people (14–24)', rows=D.index[D['youth_14_24'] == 1],
            pop='Respondents aged 14–24 in all three rounds (n=152: 62 / 46 / 44). Not a cohort.'),
}
D['p5_primary'] = (D['round'] == 3).astype(int)
reg('p5_primary', 'Paper 5 primary analysis population (Round 3)', 2, {0: 'Rounds 1–2', 1: 'Round 3'})
EXTRA[5] = ['p5_primary'] + EXTRA[5]

def nonmiss_by_round(s, df):
    return [int(s[df['round'] == r].notna().sum()) for r in (1, 2, 3)]

def codebook(df, paper):
    rows = []
    for v in df.columns:
        m = META[v]; s = df[v]
        src = m['src']
        role = ''
        if isinstance(src, int):
            role = AUD[paper].get(src, '') or ''
        if not role:
            if v in ('received', 'received_itt'): role = AUD[paper].get(43, '')
            elif v.endswith('_agree') or v.endswith('_bin') or v.endswith('_yes') or v in ('trust_high',):
                role = 'Derived'
        vals = '; '.join(f'{k} = {lab}' for k, lab in m['values'].items())
        nr = nonmiss_by_round(s, df)
        rows.append({'Variable': v, 'Label': m['label'], 'Source column #': src if src is not None else 'derived',
                     'Source questionnaire label': LAB.get(src, '') if isinstance(src, int) else '',
                     'Audit classification': role, 'Values / codes': vals,
                     'Type': 'numeric' if pd.api.types.is_numeric_dtype(s) else ('date' if pd.api.types.is_datetime64_any_dtype(s) else 'text'),
                     'n non-missing': int(s.notna().sum()), 'n Round 1': nr[0], 'n Round 2': nr[1], 'n Round 3': nr[2],
                     'Notes / derivation': m['notes']})
    return pd.DataFrame(rows)

def coverage(paper, cols):
    out = []
    for src, role in AUD[paper].items():
        vs = [v for v in SRC2VARS.get(src, []) if v in cols]
        out.append({'Audit column #': src, 'Audit classification': role, 'Questionnaire label': LAB.get(src, ''),
                    'Dataset variable(s)': ', '.join(vs) if vs else ('(stem only – see items)' if src in (53, 91, 162, 19) else 'NOT INCLUDED')})
    return pd.DataFrame(out)

import pickle
pickle.dump(dict(D=D, META=META, FLAGS=FLAGS, PAPERS=PAPERS, CORE=CORE, EXTRA=EXTRA, SES=SES_LOADINGS, LAB=LAB, AUD=AUD,
                 cb=codebook, cov=coverage), open(f'{OUT}/_state.pkl', 'wb')) if False else None

for p, cfg in PAPERS.items():
    cols = list(dict.fromkeys(CORE + EXTRA[p]))
    missing = [c for c in cols if c not in D]
    assert not missing, missing
    df = D.loc[cfg['rows'], cols].reset_index(drop=True)
    cb = codebook(df, p)
    cv = coverage(p, cols)
    assert not (cv['Dataset variable(s)'] == 'NOT INCLUDED').any(), cv[cv['Dataset variable(s)'] == 'NOT INCLUDED']
    # ---- exports
    slug = cfg['slug']
    df.to_csv(f'{OUT}/{slug}.csv', index=False)
    labels = {v: META[v]['label'][:80] for v in df.columns}
    vlabels = {v: {float(k) if k == int(k) else k: lab[:120] for k, lab in META[v]['values'].items()} for v in df.columns if META[v]['values']}
    dta = df.copy()
    for c in dta.columns:
        if pd.api.types.is_datetime64_any_dtype(dta[c]):
            dta[c] = dta[c].dt.date
    pyreadstat.write_dta(dta, f'{OUT}/{slug}.dta', column_labels=labels, variable_value_labels=vlabels, version=15)
    pyreadstat.write_sav(dta, f'{OUT}/{slug}.sav', column_labels=labels, variable_value_labels=vlabels)
    pickle.dump(dict(df=df, cb=cb, cv=cv, cfg=cfg), open(f'{OUT}/_{slug}.pkl', 'wb'))

# community-level file for Paper 5 (publishable geography)
g = D.groupby(['round', 'community_name', 'subdistrict'])
comm = g.agg(n=('resp_uid', 'size'), n_recall=('recall_mda', 'sum'),
             received_pct=('received', lambda s: round(100 * s.mean(), 1)),
             swallowed_all_pct=('swallowed_all', lambda s: round(100 * s.mean(), 1)),
             ae_any_pct=('ae_any', lambda s: round(100 * s.mean(), 1)),
             blackflies_yes_pct=('blackflies_yes', lambda s: round(100 * s.mean(), 1)),
             fast_river_pct=('fast_river', lambda s: round(100 * s.mean(), 1) if s.notna().any() else np.nan),
             river_dist_median=('river_dist_min', 'median'),
             know_flies_pct=('know_flies', lambda s: round(100 * s.mean(), 1)),
             ses_mean=('ses_index', lambda s: round(s.mean(), 2)),
             n_gps=('gps_lat', 'count'),
             centroid_lat=('gps_lat', lambda s: round(s.median(), 3)), centroid_lon=('gps_lon', lambda s: round(s.median(), 3))).reset_index()
comm['subdistrict'] = comm['subdistrict'].map(META['subdistrict']['values'])
pickle.dump(dict(comm=comm, flags=pd.DataFrame(FLAGS), ses=SES_LOADINGS, var_expl=var_expl), open(f'{OUT}/_shared.pkl', 'wb'))
print('built', {p: len(PAPERS[p]['rows']) for p in PAPERS}, 'flags', len(FLAGS), f'SES PC1 {var_expl:.1%}')
