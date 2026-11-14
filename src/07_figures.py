"""Paper 5 figures. Usage: python3 -I figures.py <results.pkl> <gisdir> <districts.shp> <outdir>"""
import sys, os, pickle
import numpy as np, pandas as pd, geopandas as gpd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Patch
from matplotlib.colors import LinearSegmentedColormap, Normalize
from scipy import stats
import matplotlib.patheffects, matplotlib.colorbar, json
CODE = json.load(open(__import__('os').environ.get('COMMUNITY_KEY', 'data/community_codes.json')))

R = pickle.load(open(sys.argv[1], 'rb')); GIS, DSHP, OUT = sys.argv[2:5]
for f in fm.findSystemFonts():
    if 'Inter' in f and 'Display' not in f: fm.fontManager.addfont(f)
plt.rcParams.update({'font.family': 'Inter', 'font.size': 8.5, 'axes.titlesize': 9, 'axes.labelsize': 8.5, 'xtick.labelsize': 8,
                     'ytick.labelsize': 8, 'axes.edgecolor': '#c9c8c2', 'axes.linewidth': 0.8, 'xtick.color': '#52514e',
                     'ytick.color': '#52514e', 'text.color': '#0b0b0b', 'axes.spines.top': False, 'axes.spines.right': False,
                     'xtick.major.size': 0, 'ytick.major.size': 0, 'savefig.dpi': 600, 'svg.fonttype': 'none', 'pdf.fonttype': 42})
SURF, GRID, MUTED, TXT2 = '#ffffff', '#e9e8e4', '#898781', '#52514e'
WATER, WATER_L = '#2a78d6', '#a9c8ef'
LOW, OK = '#eb6834', '#b9b7b0'
VIOLET = LinearSegmentedColormap.from_list('v', ['#e4e0f8', '#6250d6', '#2a1f78'])

tam = gpd.read_file(f'{GIS}/tam_district.gpkg')
nbr = gpd.read_file(f'{GIS}/neighbour_districts.gpkg')
hr = gpd.read_file(f'{GIS}/rivers_tam_region.gpkg')
osm = gpd.read_file(f'{GIS}/osm_waterways.gpkg') if os.path.exists(f'{GIS}/osm_waterways.gpkg') else None
sett = gpd.read_file(f'{GIS}/tam_communities_all.gpkg')
cent = gpd.read_file(f'{GIS}/survey_community_centroids.gpkg').set_index('community_name') if 'community_name' in gpd.read_file(f'{GIS}/survey_community_centroids.gpkg').columns else None
if cent is None:
    c = gpd.read_file(f'{GIS}/survey_community_centroids.gpkg'); cent = c.set_index(c.columns[0])
ghana = gpd.read_file(DSHP).to_crs(32630)
xmin, ymin, xmax, ymax = tam.total_bounds; padm = 3000
EXT = (xmin - padm, xmax + padm, ymin - padm, ymax + padm)

def save(fig, name):
    for a in fig.axes:
        if a.get_xlabel() in ('Easting [metre]',) or a.get_ylabel() in ('Northing [metre]',): a.set_xlabel(''); a.set_ylabel('')
    for ext in ('png', 'pdf', 'svg'): fig.savefig(f'{OUT}/{name}.{ext}', bbox_inches='tight', facecolor=SURF)
    plt.close(fig)

def base(ax, rivers_light=False):
    nbr.boundary.plot(ax=ax, color='#d9d8d3', lw=0.6, zorder=1)
    tam.plot(ax=ax, color='#f6f5f2', edgecolor='#52514e', lw=1.0, zorder=2)
    if osm is not None:
        osm[osm.waterway != 'river'].plot(ax=ax, color=WATER_L, lw=0.35, zorder=3, alpha=0.8 if not rivers_light else 0.5)
    for o, lw in [(1, .5), (2, .7), (3, 1.1), (4, 1.4), (5, 1.8), (6, 2.4), (7, 2.8)]:
        s = hr[hr.ORD_STRA == o]
        if len(s): s.plot(ax=ax, color=WATER if not rivers_light else '#8fb6e8', lw=lw * (0.8 if rivers_light else 1), zorder=4)
    ax.set_xlim(EXT[0], EXT[1]); ax.set_ylim(EXT[2], EXT[3]); ax.set_aspect('equal')
    ax.set_xticks([]); ax.set_yticks([]); ax.set_xlabel(''); ax.set_ylabel('')
    for s in ax.spines.values(): s.set_visible(False)

def scalebar(ax, km=10, loc=(0.06, 0.05)):
    x0 = EXT[0] + (EXT[1] - EXT[0]) * loc[0]; y0 = EXT[2] + (EXT[3] - EXT[2]) * loc[1]
    ax.plot([x0, x0 + km * 1000], [y0, y0], color='#0b0b0b', lw=2, solid_capstyle='butt', zorder=10)
    ax.text(x0 + km * 500, y0 + 900, f'{km} km', ha='center', va='bottom', fontsize=7.5, zorder=10)
def north(ax, loc=(0.94, 0.9)):
    x = EXT[0] + (EXT[1] - EXT[0]) * loc[0]; y = EXT[2] + (EXT[3] - EXT[2]) * loc[1]
    ax.annotate('N', xy=(x, y + 2500), xytext=(x, y), ha='center', fontsize=8, fontweight='semibold',
                arrowprops=dict(arrowstyle='-|>', color='#0b0b0b', lw=1), zorder=10)

LABEL_OFF = {'C22': (-4200, 900), 'C14': (700, -1700), 'C02': (-4300, -2300), 'C07': (900, 300), 'C03': (900, -1700), 'C20': (-1500, 900)}  # optional manual nudges (keyed by code)
LABEL_OFF = {({v: k_ for k_, v in CODE.items()}).get(k_, k_): v for k_, v in LABEL_OFF.items()}
t1 = R['table1'].set_index('community')
q = R['quadrant']

# ------------------------------------------------------------------ Figure 1: study area and perceived exposure
fig = plt.figure(figsize=(7.2, 6.0))
ax = fig.add_axes([0.0, 0.0, 0.82, 1.0])
base(ax)
sett.plot(ax=ax, color='#9a9892', markersize=1.6, zorder=5)
norm = Normalize(30, 100)
for c, r in cent.iterrows():
    if c not in t1.index or pd.isna(t1.loc[c, 'flies']): continue
    ax.scatter(r.geometry.x, r.geometry.y, s=70, color=VIOLET(norm(t1.loc[c, 'flies'])), edgecolor=SURF, linewidth=1.6, zorder=7)
for c, r in cent.iterrows():
    if c not in t1.index: continue
    dx, dy = LABEL_OFF.get(c, (900, 600))
    ax.text(r.geometry.x + dx, r.geometry.y + dy, CODE.get(c, c), fontsize=6.3, color='#0b0b0b', zorder=8,
            path_effects=[matplotlib.patheffects.withStroke(linewidth=2.2, foreground='white')])
scalebar(ax); north(ax)
# legend
cax = fig.add_axes([0.84, 0.46, 0.018, 0.22])
cb = matplotlib.colorbar.ColorbarBase(cax, cmap=VIOLET, norm=norm); cb.outline.set_visible(False)
cb.set_label('Respondents reporting\nblack flies, Round 3 (%)', fontsize=7.5); cax.tick_params(labelsize=7)
handles = [Line2D([0], [0], color=WATER, lw=2.4, label='Main river (Pra, order 6)'),
           Line2D([0], [0], color=WATER, lw=1.1, label='Tributary (order 3)'),
           Line2D([0], [0], color=WATER, lw=0.6, label='Stream (order 1–2)')]
if osm is not None: handles.append(Line2D([0], [0], color=WATER_L, lw=0.6, label='Small stream (OSM)'))
handles += [Line2D([0], [0], marker='o', color='none', markerfacecolor='#9a9892', markersize=2.5, label='Settlement (n = 226)'),
            Line2D([0], [0], marker='o', color='none', markerfacecolor='#6250d6', markeredgecolor='white', markersize=7, label='Surveyed community'),
            Patch(facecolor='#f6f5f2', edgecolor='#52514e', label='Twifo Atti-Morkwa')]
fig.legend(handles=handles, loc='lower left', bbox_to_anchor=(0.815, 0.06), frameon=False, fontsize=7)
# inset Ghana
ia = fig.add_axes([0.83, 0.74, 0.16, 0.22])
ghana.plot(ax=ia, color='#ecebe7', edgecolor='#ffffff', lw=0.2); tam.plot(ax=ia, color='#6250d6')
ia.set_xticks([]); ia.set_yticks([]); ia.set_xlabel(''); ia.set_ylabel(''); [s.set_visible(False) for s in ia.spines.values()]; ia.set_title('Ghana', fontsize=7, pad=1)
save(fig, 'Figure1_study_area_exposure')

# ------------------------------------------------------------------ Figure 2: receipt by community and round with scan clusters
cr = R['comm_round']
fig = plt.figure(figsize=(7.4, 7.6))
pos = {1: [0.0, 0.50, 0.50, 0.47], 2: [0.50, 0.50, 0.50, 0.47], 3: [0.0, 0.0, 0.50, 0.47]}
titles = {1: 'A  Round 1 · ivermectin', 2: 'B  Round 2 · moxidectin', 3: 'C  Round 3 · moxidectin'}
LOFF2 = {'C22': (-4200, 900), 'C14': (700, -1700), 'C02': (-4300, -2300), 'C03': (900, -1700),
         'C20': (-1500, 900), 'C09': (-5200, -1500), 'C21': (900, -1500),
         'C16': (-2600, -2000), 'C01': (-1800, -2100), 'C08': (-2000, 1300), 'C05': (900, 300)}
_NAME = {v: k_ for k_, v in CODE.items()}  # label nudges are keyed by public code; map back to names
LOFF2 = {_NAME.get(k_, k_): v for k_, v in LOFF2.items()}
for k in (1, 2, 3):
    ax = fig.add_axes(pos[k]); base(ax)
    sett.plot(ax=ax, color='#9a9892', markersize=0.9, zorder=5)
    CL = R['scan'][k]['clusters']
    sig = [cl for cl in CL if cl['p'] < 0.05]
    bord = [cl for cl in CL if 0.05 <= cl['p'] < 0.10]
    for cl in sig:
        ax.add_patch(Circle((cl['cx'], cl['cy']), max(cl['r'], 1200) + 800, fc='#eb6834', alpha=0.08, ec='none', zorder=6))
        ax.add_patch(Circle((cl['cx'], cl['cy']), max(cl['r'], 1200) + 800, fill=False, ec='#0b0b0b', lw=1.1, zorder=8))
    for cl in bord:
        ax.add_patch(Circle((cl['cx'], cl['cy']), max(cl['r'], 1200) + 800, fill=False, ec='#0b0b0b', lw=1.0, ls=(0, (3, 2)), zorder=8))
    incl = {c for cl in sig + bord for c in cl['communities']}
    for c, r in cent.iterrows():
        if c not in cr.index or pd.isna(cr.loc[c, k]): continue
        p = cr.loc[c, k]
        ax.scatter(r.geometry.x, r.geometry.y, s=40, color=LOW if p < 0.8 else OK, edgecolor=SURF, linewidth=1.3, zorder=9)
        if p < 0.8 or c in incl:
            dx, dy = LOFF2.get(c, (800, 600))
            ax.text(r.geometry.x + dx, r.geometry.y + dy, f'{CODE.get(c, c)} {100 * p:.0f}%', fontsize=5.6, zorder=10,
                    color='#0b0b0b' if p < 0.8 else TXT2,
                    path_effects=[matplotlib.patheffects.withStroke(linewidth=2, foreground='white')])
    nsig = len(sig)
    sub = f'{nsig} cluster{"s" if nsig != 1 else ""} of non-participation at p<0·05' if nsig else 'No cluster at p<0·05'
    if bord and not nsig: sub = f'Borderline cluster of non-participation (p={bord[0]["p"]:.3f})'.replace('.', '·')
    ax.set_title(f'{titles[k]}\n{sub}', loc='left', fontsize=8, pad=2)
    scalebar(ax, km=10, loc=(0.06, 0.05)); north(ax)
# legend panel with Ghana inset
ia = fig.add_axes([0.63, 0.24, 0.22, 0.20])
ghana.plot(ax=ia, color='#ecebe7', edgecolor='#ffffff', lw=0.2); tam.plot(ax=ia, color='#52514e')
ia.set_xticks([]); ia.set_yticks([]); ia.set_xlabel(''); ia.set_ylabel(''); [s_.set_visible(False) for s_ in ia.spines.values()]
ia.set_title('Twifo Atti-Morkwa, Ghana', fontsize=7, pad=1)
leg = [Line2D([0], [0], marker='o', color='none', markerfacecolor=LOW, markeredgecolor='white', markersize=7, label='Community participation below 80% (labelled)'),
       Line2D([0], [0], marker='o', color='none', markerfacecolor=OK, markeredgecolor='white', markersize=7, label='Community participation 80% or above'),
       Line2D([0], [0], color='#0b0b0b', lw=1.1, label='Scan cluster of non-participation, p<0·05'),
       Line2D([0], [0], color='#0b0b0b', lw=1, ls=(0, (3, 2)), label='Scan cluster, 0·05≤p<0·10'),
       Line2D([0], [0], color=WATER, lw=2.4, label='Main river (Pra, order 6)'),
       Line2D([0], [0], color=WATER, lw=1.1, label='Tributary (order 3)'),
       Line2D([0], [0], color=WATER, lw=0.6, label='Stream (order 1–2)')]
if osm is not None: leg.append(Line2D([0], [0], color=WATER_L, lw=0.6, label='Small stream (OSM)'))
leg.append(Line2D([0], [0], marker='o', color='none', markerfacecolor='#9a9892', markersize=2.5, label='Settlement (n = 226)'))
fig.legend(handles=leg, loc='upper left', bbox_to_anchor=(0.56, 0.22), frameon=False, fontsize=6.8)
save(fig, 'Figure2_receipt_clusters_by_round')

# ------------------------------------------------------------------ Figure 3: persistence of community participation across rounds
pl = R['rev']['persistent']
fig, ax = plt.subplots(figsize=(6.4, 4.4))
ax.axhline(80, color=MUTED, lw=0.9, zorder=1); ax.text(3.32, 80.8, '80%', fontsize=7, color=TXT2, va='bottom', ha='right')
STY = {'Below 80% in all three rounds': ('#c0401a', 1.8, 3), 'Below 80% in two rounds': ('#eb6834', 1.2, 2)}
labs = []
for c, r in pl.iterrows():
    xs = [k for k in (1, 2, 3) if pd.notna(r[k])]; ys = [100 * r[k] for k in xs]
    col, lw, z = STY.get(r.status, ('#c9c8c2', 0.9, 1))
    ax.plot(xs, ys, color=col, lw=lw, zorder=z, alpha=0.95)
    ax.scatter(xs, ys, s=22 if z > 1 else 12, color=col, edgecolor=SURF, linewidth=0.8, zorder=z + 1)
    if r.status in STY and pd.notna(r[3]): labs.append((100 * r[3], r.code, col))
labs.sort()
last = -99
for y, code, col in labs:
    y2 = max(y, last + 2.6); last = y2
    ax.text(3.08, y2, code, fontsize=6.8, color=col, va='center', fontweight='semibold')
ax.set_xticks([1, 2, 3]); ax.set_xticklabels(['Round 1\nivermectin', 'Round 2\nmoxidectin', 'Round 3\nmoxidectin'])
ax.set_xlim(0.85, 3.35); ax.set_ylim(40, 102)
ax.set_ylabel('Community participation among recallers (%)'); ax.grid(axis='y', color=GRID, lw=0.8); ax.set_axisbelow(True); ax.spines['left'].set_visible(False)
leg = [Line2D([0], [0], color='#c0401a', lw=1.8, label='Below 80% in all three rounds'), Line2D([0], [0], color='#eb6834', lw=1.2, label='Below 80% in two rounds'),
       Line2D([0], [0], color='#c9c8c2', lw=0.9, label='Other communities')]
ax.legend(handles=leg, frameon=False, fontsize=7.2, loc='lower left', ncol=3, bbox_to_anchor=(0.0, -0.32))
save(fig, 'Figure3_persistence_by_community')

# ------------------------------------------------------------------ Figure 4: distance spline + agreement
cv = R['rev']['curve']
fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.2, 3.2), gridspec_kw=dict(width_ratios=[1.15, 1]))
a1.fill_between(cv.km, 100 * cv.lo, np.minimum(100 * cv.hi, 100), color='#2a78d6', alpha=0.12, lw=0)
a1.plot(cv.km, 100 * cv.est, color='#2a78d6', lw=2)
a1.axhline(80, color=MUTED, lw=0.9)
for v in R['rev']['hh_dist']:
    a1.plot([v, v], [41, 43], color='#52514e', lw=0.4, alpha=0.5)
a1.set_xscale('log'); a1.minorticks_off(); a1.set_xticks([0.1, 0.3, 1, 3, 10]); a1.set_xticklabels(['0·1', '0·3', '1', '3', '10'])
a1.set_ylim(40, 101); a1.set_xlabel('Distance to nearest larger river (km, log scale)'); a1.set_ylabel('Standardised community participation (%)')
a1.grid(axis='y', color=GRID, lw=0.8); a1.set_axisbelow(True); a1.spines['left'].set_visible(False)
w = R['model2_spline_wald']
a1.set_title(f'A  Participation by distance (spline p={w[2]:.2f})'.replace('.', '·'), loc='left', fontsize=8.5)
t = R['table1']; t = t[t.community != 'All communities']
a2.scatter(t.d_big, t.self_min, s=32, color='#6250d6', edgecolor=SURF, linewidth=1.2, zorder=3)
a2.set_xscale('log'); a2.minorticks_off(); a2.set_xticks([0.3, 1, 3, 10]); a2.set_xticklabels(['0·3', '1', '3', '10'])
ag = R['agreement'].set_index('var').loc['d_big']
a2.set_title(f'B  Self-reported vs mapped, community level (ρ={ag.rho_comm:.2f})'.replace('.', '·'), loc='left', fontsize=8.5)
a2.set_xlabel('Median distance to larger river (km, log scale)'); a2.set_ylabel('Median self-reported round trip (min)')
a2.grid(color=GRID, lw=0.8); a2.set_axisbelow(True); a2.spines['left'].set_visible(False)
fig.tight_layout(w_pad=2)
save(fig, 'Figure4_distance_receipt_and_agreement')
print('figures written')
