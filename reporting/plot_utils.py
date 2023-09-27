import numpy as np
import pandas as pd

# plotting
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from matplotlib.lines import Line2D

# AI
from sklearn.cluster import KMeans

# memory buffer
from io import BytesIO

# utils
from itertools import groupby, cycle, islice, repeat
from textwrap import fill

# 回復預設字型設定
mpl.rcParams.update(mpl.rcParamsDefault)

FONT = FontProperties(fname="reporting\\SimHei.ttf", size=14)

COLOR = {
    'red-accent3': '#E0301E',
    'red-accent5-25%': '#AC2139',
    'red-accent3-40%': '#ED8278',
    'gold-accent2': '#FFB600',
    'gold-accent2-40%': '#FFD366',
    'gold-accent2-60%': '#FFE299',
    'dark-gray-accent6-40%': '#909090',
    'brown-accent1-40%': '#FD8A4D',
    'green': '#92D050'
}


FIN_PERFORMANCE_CHART_COLORS = {
    'cost_of_goods_sold_rate': 'red-accent5-25%',
    'days_payable_outstanding': 'dark-gray-accent6-40%',
    'inventory_days': 'gold-accent2-40%',
    'days_sales_outstanding': 'gold-accent2-40%',
    'employee_productivity': 'brown-accent1-40%',
    'fixed_assets_turnover_ratio': 'red-accent5-25%',
    'operating_expense_rate': 'brown-accent1-40%',
    'revenue_growth_rate': 'dark-gray-accent6-40%'
}


FIN_SENSITIVITY_CHART_COLORS = [
    COLOR['red-accent3-40%'], COLOR['gold-accent2-40%'], COLOR['dark-gray-accent6-40%'],
    COLOR['brown-accent1-40%'], COLOR['gold-accent2-60%'], COLOR['red-accent3'],
    COLOR['green'], COLOR['gold-accent2']
]


END_INTERVAL = [0.1, 0.5, 1, 5, 10, 100, 200, 1000, 5000, 10000, 100000, 1000000, 10000000, 100000000, 1000000000]

def fin_performance(name: str, df: pd.DataFrame) -> BytesIO:
    print(name)
    print(df)
    # switch font style to default.
    mpl.rcParams['font.family'] = 'sans-serif'
    mpl.rcParams['font.sans-serif'] = 'DejaVu Sans'

    color = COLOR[FIN_PERFORMANCE_CHART_COLORS[name]]

    # columns to be drawn as bar.
    y_label = ['value', 'bar_end']

    min_value, max_value = df.min()['value'], df.max()['value']
    abs_max_value = max(abs(max_value), abs(min_value))
    use_percentage = True if abs_max_value < 1 else False

    # choose proper interval for bar end boundry
    i = 0
    bar_end = END_INTERVAL[i]
    while bar_end < abs_max_value:
        i += 1
        bar_end = END_INTERVAL[i]
    
    # calulate length for white space
    df['bar_end'] = bar_end - df['value']
    df.loc[(df['value'] < 0), 'bar_end'] = bar_end
    
    # if negative bar end is needed
    if min_value < 0:
        df['negative_bar_end'] = 0 - bar_end - df['value']
        df.loc[(df['value'] > 0), 'negative_bar_end'] = 0 - bar_end
        y_label.append('negative_bar_end')

    # create horizontal bar chart
    fig = Figure()
    fig.subplots_adjust(left=0.125, bottom=0.3, right=0.95, top=0.55)
    ax = fig.add_subplot(111)
    
    df.plot.barh(
        ax=fig.gca(),
        x='year', y=y_label, stacked=True,
        color={'value': color, 'bar_end': 'white', 'negative_bar_end': 'white'},
        edgecolor = color)

    # bar label formatting
    bars: list[mpl.container.BarContainer] = [thing for thing in ax.containers if isinstance(thing, mpl.container.BarContainer)]
    bar_labels = list(bars[0].datavalues)

    idx_max = bar_labels.index(max(bars[0].datavalues))
    idx_min = bar_labels.index(min(bars[0].datavalues))

    for idx in range(len(bar_labels)):

        if use_percentage:
            temp = str(round(bar_labels[idx] * 100, 2)) + "%"
        else:
            temp = str(round(bar_labels[idx], 2))

        if idx == idx_max:
            bar_labels[idx] = f'{temp} ⬆️'
        elif idx == idx_min:
            bar_labels[idx] = f'{temp} ⬇️'
        else:
            bar_labels[idx] = f'{temp}'

    ax.bar_label(container=bars[1], label_type='edge', labels=bar_labels, padding=8, color=color)
    
    # chart formatting
    ax.get_legend().remove()
    
    # disable chart spines
    for axis in ['top', 'bottom', 'left', 'right']:
        ax.spines[axis].set_linewidth(0)

    # ticks
    ax.set_ylabel('')
    ax.get_xaxis().set_visible(False)
    ax.tick_params(axis='both', which='major', colors=color, length=0) #y, hide tick

    if use_percentage:
        ax.xaxis.set_major_formatter(mpl.ticker.PercentFormatter(xmax=1))

    # hide tick label
    #plt.setp(ax.get_xticklabels(), visible=False)                       # hide tick label   

    buffer = BytesIO()
    fig.savefig(buffer, format='png', dpi=300, bbox_inches='tight', pad_inches=0, transparent=True)
    buffer.seek(0)

    return buffer


def fin_sensitivity(df: pd.DataFrame) -> BytesIO:

    mpl.rcParams['font.family'] = 'sans-serif'
    mpl.rcParams['font.sans-serif'] = 'DejaVu Sans'
    
    # x_labels formatting
    df['fin_indicator_text_en'] = df.apply(lambda row: str(row['fin_indicator_text_en']).replace('_sensitivity', '').replace('_', ' '), axis=1)
    df['fin_indicator_labels'] = df.apply(lambda row: fill(row['fin_indicator_text_en'], 12), axis=1)   # text wrapping
    colors = list(islice(cycle(FIN_SENSITIVITY_CHART_COLORS), None, len(df)))                           # based on length of df, generate color list cyclic

    # plotting
    #mpl.rcParams.update(mpl.rcParamsDefault)
    fig = Figure(figsize=(12, 5.4))
    fig.subplots_adjust(left=0.08, bottom=0.11, right=0.94, top=0.88)

    ax = fig.add_subplot(111)    

    df.plot.bar(ax=fig.gca(), x='fin_indicator_labels', y='value', 
        rot=0, color=colors, width=0.35)

    bars: list[mpl.container.BarContainer] = [thing for thing in ax.containers if isinstance(thing, mpl.container.BarContainer)]
    ax.bar_label(container=bars[0], label_type='edge', padding=8)

    # chart formatting    
    for axis in ['top', 'right']:
        ax.spines[axis].set_linewidth(0)

    ax.get_legend().remove()
    ax.grid(axis='y', linestyle='--')

    # output formatting
    ax.tick_params(axis='x', which='major', length=10, width=0)
    ax.tick_params(axis='y', which='major', length=7, grid_linestyle='--')
    
    buffer = BytesIO()
    fig.savefig(buffer, format='png', bbox_inches='tight', pad_inches=0, transparent=True, dpi=300)
    buffer.seek(0)

    return buffer


def solution_priority_matrix(df_solution: pd.DataFrame) -> BytesIO:
    """"
    mpl.rcParams['font.family'] = 'monospace'
    mpl.rcParams['font.monospace'] = 'Microsoft JhengHei'
    #mpl.rcParams['font.sans-serif'] = 'SimHei'
    """
    
    data = df_solution.copy(deep=True)
    data = data.reset_index(drop=True)
    print(data)
    # Build cluster model
    #model = KMeans(n_clusters=2, n_init='auto')
    #cluster = model.fit_predict(data.iloc[:, 1:4])
    #centers = model.cluster_centers
    data["final_score_ori"] = data["final_score"]
    #data["cluster"] = cluster

    # 將資料標準化，已獲得相對推薦優先度
    data.iloc[:, 1:4] = normalize_data(data.iloc[:, 1:4])

    # data prepare
    x = data['sf_score']
    y = data['sq_score']
    colors = data["final_score_ori"]
    sizes = 5000+(15000*(data['final_score']))

    # figure init
    fig = Figure(figsize=(16, 14),dpi = 300)
    ax = fig.add_subplot(111)

    # scatter plot
    
    # Create a gradient color map using the initial colors
    cmap = plt.cm.get_cmap("OrRd")
    norm = plt.Normalize(min(colors), max(colors))
    color_map = cmap(norm(colors))


    ax.scatter(x, y, c=color_map, s=sizes, alpha=0.8)
    
    
    # 為 scatter plot 標記解決方案名稱
    for i in range(len(data)):
        ax.annotate(
            text= str(i+1),
            xy=(data.loc[i, 'sf_score'], data.loc[i, 'sq_score']-0.02),
            fontsize=50, color='black', ha="center"
        )
        
    """
    group_0 = data.iloc[np.ix_(data['cluster'] == 0)]
    group_1 = data.iloc[np.ix_(data['cluster'] == 1)]

    c0_reg = np.polyfit(group_0["sf_score"],
                        group_0["sq_score"], 1)
    c1_reg = np.polyfit(group_1["sf_score"],
                        group_1["sq_score"], 1)

    x_fitmin = min(group_0["sf_score"].min(), group_1["sf_score"].min())
    x_fitmax = max(group_0["sf_score"].max(), group_1["sf_score"].max())
    x_fit = np.linspace(x_fitmin, x_fitmax, 100)

    sep = np.poly1d(np.mean([c0_reg, c1_reg], axis=0))
    
    ax.plot(x_fit, sep(x_fit), color="red", ls="dashed", label="separator")
    ax.set_xlim([-0.1, 1.1])
    ax.set_ylim([-0.1, 1.1])
    """

    # 報表外觀設定
    ax.axhline(y=0.5, color='black', linestyle='-')
    ax.axvline(x=0.5, color='black', linestyle='-')
    
    """
    ax.axvspan(xmin=-0.1, xmax=0.5, ymin=0.5, ymax=1, alpha=0.3, color='navajowhite')
    ax.axvspan(xmin=0.5, xmax=1.1, ymin=0, ymax=0.5, alpha=0.3, color='navajowhite')
    ax.axvspan(xmin=0.5, xmax=1.1, ymin=0.5, ymax=1, alpha=0.3, color='sandybrown')
    ax.axvspan(xmin=-0.1, xmax=0.5, ymin=0, ymax=0.5, alpha=0.3, color='sandybrown')

    ax.text(0.2, 0.4, '暫時捨棄區', style='italic', fontsize=20, alpha=0.3, ha="center", fontproperties=FONT)
    ax.text(0.8, 0.4, '等待實施機會區', style='italic', fontsize=20, alpha=0.3, ha="center", fontproperties=FONT)
    ax.text(0.2, 1.0, '注意力集中區', style='italic', fontsize=20, alpha=0.3, ha="center", fontproperties=FONT)
    ax.text(0.8, 1.0, '立即執行區', style='italic', fontsize=20, alpha=0.3, ha="center", fontproperties=FONT)
    """

    # 輸出
    buffer = BytesIO()
    fig.savefig(buffer, format='png', bbox_inches='tight', pad_inches=0.5, transparent=True, dpi=300)
    buffer.seek(0)

    return buffer

def normalize_data(data):
    return (data - np.min(data)) / (np.max(data) - np.min(data))

"""
def qualitative_detail(df_qualitative_result: pd.DataFrame) -> BytesIO:
    # aspect: (大分類)質化題目所在的問題面相 -> 數位營運、數位人才、新科技、顧客體驗...
    # module: (中分類)質化題目所代表的議題、模組 -> 物聯網、資訊安全、雲端運算...

    mpl.rcParams['font.family'] = 'monospace'
    mpl.rcParams['font.monospace'] = 'Microsoft JhengHei'
    
    df = df_qualitative_result.groupby(['aspect', 'module']).mean(numeric_only=True)
    df = df.iloc[:,[1,2]]
    
    fig = Figure(figsize=(12, 9))
    ax = fig.add_subplot(111)

    # 設定顏色
    aspect_count = df.index.get_level_values(0).nunique()
    aspects = df.index.get_level_values(0).unique()

    colors = []
    colors_cycle = list(islice(cycle(FIN_SENSITIVITY_CHART_COLORS), None, aspect_count))

    for i in range(aspect_count):
        # 找到大分類內的中分類數量
        module_count = df.loc[ aspects[i] ].index.get_level_values(0).nunique()
        # 將大分類內的所有中分類，給予同一種顏色
        colors_i = list(repeat(colors_cycle[i] , module_count))
        colors = colors + colors_i

    # 作圖
    df['target'].plot.barh( ax=fig.gca(), rot=0, width=0.8, color=colors, alpha=0.4)
    df['actual'].plot.barh( ax=fig.gca(), rot=0, width=0.8, color=colors)

    # remove default labels
    labels = ['' for item in ax.get_yticklabels()]
    ax.set_yticklabels(labels)
    ax.set_ylabel('')

    # set group bar labels
    label_group_bar_table(ax, df)

    legend = ax.legend(prop=FONT)
    legend.get_texts()[0].set_text('期望分數')
    legend.get_texts()[1].set_text('實際分數')

    for axis in ['top', 'right']:
        ax.spines[axis].set_linewidth(0)

    ax.set_xlabel('分數')
    ax.set_ylabel('面相')
    ax.xaxis.set_label_coords(1.05, -0.01)
    ax.yaxis.set_label_coords(-0.01, 1.05)

    # make arrows
    ax.plot(1, -0.65, ls="", marker=">", ms=10, color="k",
        transform=ax.get_yaxis_transform(), clip_on=False)
    ax.plot(0, 1.05, ls="", marker="^", ms=10, color="k",
        transform=ax.get_xaxis_transform(), clip_on=False)
    line = Line2D([0, 0], [1, 1.05], lw=0.7, transform=ax.transAxes, color='black')
    line.set_clip_on(False)
    ax.add_line(line)
    

    fig.subplots_adjust(bottom=.1 * df.index.nlevels)
    buffer = BytesIO()
    fig.savefig(buffer, format='png', bbox_inches='tight', pad_inches=0.5, transparent=True, dpi=300)
    buffer.seek(0)

    return buffer


def label_len(my_index, level):
    labels = my_index.get_level_values(level)
    return [(k, sum(1 for i in g)) for k, g in groupby(labels)]


def label_group_bar_table(ax, df):
    xpos = 0.01
    scale = 1. / df.index.size
    for level in range(df.index.nlevels)[::-1]:
        pos = -0.15
        for label, rpos in label_len(df.index, level):
            lypos = (pos + .5 * rpos) * scale
            ax.text(xpos, lypos, label, ha='left', transform=ax.transAxes, fontproperties=FONT)
            #add_line(ax, xpos, pos * scale+0.005)
            pos += rpos
        #add_line(ax, xpos, pos * scale+0.005 )
        xpos -= .08

"""
   
def qualitative_detail(df_qualitative_result: pd.DataFrame, aspect: str, aspect_idx: int) -> BytesIO:
    # aspect: (大分類)質化題目所在的問題面相 -> 數位營運、數位人才、新科技、顧客體驗...
    # module: (中分類)質化題目所代表的議題、模組 -> 物聯網、資訊安全、雲端運算...

    mpl.rcParams['font.family'] = 'monospace'
    mpl.rcParams['font.monospace'] = 'Microsoft JhengHei'
    mpl.rcParams.update({'font.size': 10})
    
    df = df_qualitative_result
    df = df.iloc[:,[1,2]]
    df = df.loc[aspect]
    
    fig = Figure(figsize=(10, 8), dpi=100)
    ax = fig.add_subplot(111)

    # 設定顏色
    aspect_count = df.index.get_level_values(0).nunique()
    colors = []
    colors_cycle = list(islice(cycle(FIN_SENSITIVITY_CHART_COLORS), None, aspect_count))

    # 找到大分類內的中分類數量
    module_count = df.index.get_level_values(0).nunique()
    # 將大分類內的所有中分類，給予同一種顏色
    colors = list(repeat(colors_cycle[aspect_idx] , module_count))
   

    # 作圖
    df['target'].plot.barh( ax=fig.gca(), rot=0, width=0.8, color=colors, alpha=0.4)
    df['actual'].plot.barh( ax=fig.gca(), rot=0, width=0.8, color=colors)

    # remove default labels
    labels = ['' for item in ax.get_yticklabels()]
    ax.set_yticklabels(labels)
    ax.set_ylabel('')

    # set group bar labels
    label_group_bar_table(ax, df)
    ax.text(-.1, 0.5, aspect, ha='left', transform=ax.transAxes, fontproperties=FONT)


    legend = ax.legend(prop=FONT)
    legend.get_texts()[0].set_text('期望分數')
    legend.get_texts()[1].set_text('實際分數')

    for axis in ['top', 'right']:
        ax.spines[axis].set_linewidth(0)

    ax.set_xlabel('分數')
    ax.set_ylabel('面相')
    ax.xaxis.set_label_coords(1.05, -0.01)
    ax.yaxis.set_label_coords(-0.01, 1.05)

    # make arrows
    ax.plot(1, -0.65, ls="", marker=">", ms=10, color="k",
        transform=ax.get_yaxis_transform(), clip_on=False)
    ax.plot(0, 1.05, ls="", marker="^", ms=10, color="k",
        transform=ax.get_xaxis_transform(), clip_on=False)
    line = Line2D([0, 0], [1, 1.05], lw=0.7, transform=ax.transAxes, color='black')
    line.set_clip_on(False)
    ax.add_line(line)
    
    #save = str(aspect_idx) + "test.png"
    #fig.savefig(save)
    
    fig.subplots_adjust(bottom=.1 * df.index.nlevels)
    buffer = BytesIO()
    fig.savefig(buffer, format='png', bbox_inches='tight', pad_inches=0.5, transparent=True, dpi=300)
    buffer.seek(0)

    return buffer


def label_len(my_index, level):
    labels = my_index.get_level_values(level)
    return [(k, sum(1 for i in g)) for k, g in groupby(labels)]


def label_group_bar_table(ax, df):
    xpos = 0.01
    scale = 1. / df.index.size
    for level in range(df.index.nlevels)[::-1]:
        pos = -0.15
        for label, rpos in label_len(df.index, level):
            lypos = (pos + .5 * rpos) * scale
            ax.text(xpos, lypos, label, ha='left', transform=ax.transAxes, fontproperties=FONT )
            #add_line(ax, xpos, pos * scale+0.005)
            pos += rpos
        #add_line(ax, xpos, pos * scale+0.005 )
        xpos -= .08

def interviewee_plots(df): 
    # Create the bar chart
    fig, ax = plt.subplots(figsize=(8, 5))
    
    # Set the width of the bars
    bar_width = 0.3
    ax.bar(df['weight_key'], df['gap'], bar_width, color= 'grey')
    
    # Add labels to the bars and under the values
    for i, val in enumerate(df['gap']):
        ax.text(i, val/2, str(val), ha='center', va='center', fontsize=12, color='white')
        ax.text(i, val/2-0.2, df['weight_key'][i], ha='center', fontsize=12, color='black')
    
    # Set the x-axis limits    
    ax.set_xlim([-1, 2])
    # Add labels to the x-axis
    ax.set_xticklabels([])

    # Add title below the x-axis
    ax.set_title(df['module'][0], fontsize=16, y=-0.2)

    # Remove y-axis
    ax.spines['left'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.set_yticks([])

    # display plot
    #plt.show()
    
    buffer = BytesIO()
    fig.savefig(buffer, format='png', bbox_inches='tight', pad_inches=0.5, transparent=True, dpi=300)
    buffer.seek(0)

    return buffer