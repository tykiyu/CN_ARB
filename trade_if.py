import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import pyecharts.options as opts
from pyecharts.charts import Bar, Grid, Line, Liquid, Page, Pie,Timeline,Tab
from pyecharts.faker import Faker
import os
pd.set_option('display.max_rows', 1000)

def get_log(name,path,ct,date,shape,buy_color,sell_color,opac):
    trade_df = pd.read_csv(path + '\\tradeinfo.csv', header = None,usecols = [0,1,2,3,4],names = ['Time','Direction','Contract','Price','Lot'])
    wm = lambda x: np.average(x, weights=trade_df.loc[x.index, "Lot"])
    avgp = lambda x: x/trade_df.loc[x.index, "trade_lot"]
    trade_df.Time = pd.to_datetime(trade_df.Time.values,format = '%Y-%m-%d_%H:%M:%S.%f')
    test = trade_df.set_index('Time').loc[date].reset_index()
    test['cn_trade'] = test.Price > 10000
    test['dir'] = [-1 if x == 'sell' else 1 for x in test.Direction.values]
    test['cn_lot'] = test.Lot * test.cn_trade * test.dir
    test['trade_lot'] = test.Lot * test.dir
    test['cum_lot'] = test.cn_lot.cumsum()
    test['order_id'] = None
    test['prod_price'] = test.trade_lot * test.Price
    order_id = 1
    for i, row in test.iterrows():
        if i == 0:
            test.loc[i,'order_id'] = order_id
            continue
        if row['cn_lot'] != 0 and test.loc[i-1,'cum_lot']%30 == 0:
            order_id = order_id + 1
        test.loc[i,'order_id'] = order_id
    res = test.groupby(['order_id','Contract']).agg(Time = ('Time','first'),Direction = ('Direction','last'),Lot = ('trade_lot','sum'),Price = ('Price',wm),P = ('prod_price','sum')).sort_values(by = ['Time','Contract'],ascending = [True,False])
    res = res.reset_index().set_index('Time')
    res.rename(columns = {'Price':'VWAP','P':'Price'},inplace = True)
    log = res.loc[res.Contract == ct]
    log.index = log.index.floor('10s')
    marker = [opts.MarkPointItem( coord=[i, x['VWAP']],
                                  value= x['Lot'], 
                                  symbol = shape,
                                  symbol_size = [27,27] if shape =='pin' else [23,23],
                                  itemstyle_opts = opts.ItemStyleOpts( color=buy_color if x['Direction'] == 'buy' else sell_color,opacity = opac)
                                ) 
                   for i,x in  log.iterrows() ]
    t = [opts.MarkPointItem( coord=[i, name],
                                  value= x['Lot'], 
                                  symbol = 'circle',
                                  symbol_size = [23,23],
                                  itemstyle_opts = opts.ItemStyleOpts( color='red' if x['Direction'] == 'buy' else 'green',opacity = 0.3)
                                ) 
                   for i,x in  log.iterrows() ]
    return t,marker
	
def if_get_grid(d,b):
# *********************************     Read Data     ***************************************#
    sheets = ['SHSN300 Index','IFB1 Index','SSE50 Index','FFB1 Index','SH000905 Index','FFD1 Index','XIN9I Index','XU1 Index']
    datamap = pd.read_excel(".\\股指数据\\{}.xlsx".format(d), sheet_name=sheets, index_col=0,skiprows = [0,1,2])
    agdata = None
    for key in datamap:
        if agdata is None:
            agdata = datamap[key]
        else:
            agdata = agdata.merge(datamap[key],on = 'Dates')
    agdata.columns = sheets
    agdata = (agdata.between_time('13:00','11:30')).between_time('9:30','15:00')





    # params at the beginning of the day

#*************************************     Calc Theo Data    ******************************************#
    margin = 20
    bbase = b
    base = b
    distor = 4
    
    agdata['Theo_A50'] =  agdata['XIN9I Index'] * (agdata['IFB1 Index'] * 9 - agdata['FFD1 Index'] * 2) / (agdata['SHSN300 Index'] * 9 - agdata['SH000905 Index'] * 2)
    agdata['Base'] = base
    for i,row in agdata.iterrows():
        if row['XU1 Index'] >= row['Theo_A50'] + base + margin:
            base += distor
            agdata.loc[i,'Dir'] = 'Sell'
        if row['XU1 Index'] <= row['Theo_A50'] + base - margin:
            base -= distor
            agdata.loc[i,'Dir'] = 'Buy'

        agdata.loc[i,'Base'] = base
        agdata.loc[i,'Lower'] = round(row['Theo_A50']) + base - margin
        agdata.loc[i,'Upper'] = round(row['Theo_A50']) + base + margin
        agdata.loc[i,'Layers'] = (base - bbase)/distor

    sell = agdata[agdata.Dir == 'Sell']
    buy = agdata[agdata.Dir == 'Buy']

    sell_series = [opts.MarkPointItem(name="sell",
                                      coord=[i, x['XU1 Index']],
                                      value= None, 
                                      symbol = 'circle',
                                      symbol_size = [40,40],
                                      itemstyle_opts = opts.ItemStyleOpts( color='green',opacity = 0.12,),

                                     ) 
                   for i,x in  sell.iterrows() ]
    buy_series  = [opts.MarkPointItem(name="buy",
                                      coord=[i, x['XU1 Index']],
                                      value= None, 
                                      symbol = 'circle',
                                      symbol_size = [40,40],
                                      itemstyle_opts = opts.ItemStyleOpts( color='red', opacity = 0.12,)
                                     ) 
                   for i,x in  buy.iterrows() ]
    trade_t =  [opts.MarkPointItem(
                                      coord=[i, 'Theo'],
                                      value= None, 
                                      symbol = 'circle',
                                      symbol_size = [35,35],
                                      itemstyle_opts = opts.ItemStyleOpts( color='red',opacity = 0.12,),

                                     ) 
                   for i,x in  buy.iterrows() ] +[opts.MarkPointItem(
                                                                          coord=[i, 'Theo'],
                                                                          value= None, 
                                                                          symbol = 'circle',
                                                                          symbol_size = [35,35],
                                                                          itemstyle_opts = opts.ItemStyleOpts( color='green',opacity = 0.12,),

                                                                         ) 
                                                       for i,x in  sell.iterrows() ]
    trade_series = sell_series + buy_series
    
#*************************************     Read  Log    ******************************************#
    if_pathmap = {}
    if_pathmap['tj'] = 'E:\\tj\\tj_股指\\Algo_kk_if\\'
    if_pathmap['sy'] = 'E:\\sy\\sy_股指\\Algo_kk_if\\'
    if_pathmap['ty'] = 'T:\\index_quoter_rebalanced\\Algo_kk_if\\'
    if_pathmap['xx'] = 'X:\\Algo_kk_if\\'
    if_pathmap['dy'] = 'Y:\\Algo_kk_if\\'
    if_pathmap['gxm'] = 'Z:\\Algo_kk_if\\'
    if_pathmap['ting'] = '.\\交易日志\\'
    if_pathmap['lm'] = '.\\股指数据\\'
    lm_t,lm_marker = get_log('sy',if_pathmap['sy'],'SGX_CN_2101',d,'pin','purple','blue',0.6)
    tj_t,tj_marker = get_log('tj',if_pathmap['tj'],'SGX_CN_2101',d,'pin','red','green',0.6)
    sy_t,sy_marker = get_log('sy',if_pathmap['sy'],'SGX_CN_2101',d,'pin','#FF9900','cyan',0.7)
    xx_t,xx_marker = get_log('xx',if_pathmap['xx'],'SGX_CN_2101',d,'circle','red','green',0.6)
    gxm_t,gxm_marker = get_log('gxm',if_pathmap['gxm'],'SGX_CN_2101',d,'circle','#FF9900','cyan',0.7)
    dy_t,dy_marker = get_log('dy',if_pathmap['dy'],'SGX_CN_2101',d,'diamond','FF9900','cyan',0.7)
    ty_t,ty_marker = get_log('ty',if_pathmap['ty'],'SGX_CN_2101',d,'diamond','red','green',0.6)
    ting_t,ting_marker = get_log('ting',if_pathmap['ting'],'SGX_CN_CN Jan21',d,'rect','red','green',0.6)

#*************************************     Draw  Chart    ******************************************#

    a50_line = (
        Line(
            init_opts=opts.InitOpts(
                animation_opts=opts.AnimationOpts(animation=False)
            )
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(title="IF Trade Log -- "+d),
            xaxis_opts=opts.AxisOpts(
                axistick_opts=opts.AxisTickOpts(is_align_with_label=True),
                is_scale=False,
                boundary_gap=False,
            ),
            yaxis_opts=opts.AxisOpts(
                name='CN2101',
                is_scale=True,
                splitarea_opts=opts.SplitAreaOpts(
                    is_show=True,
                    areastyle_opts=opts.AreaStyleOpts(opacity=2),
                )
            ),
            datazoom_opts=[
                opts.DataZoomOpts(
                    is_show=True, type_="inside", xaxis_index=[0,1], range_end=100
                ),
                opts.DataZoomOpts(
                    is_show=True, type_="slider", xaxis_index=[0,1], range_end=100,
                    pos_bottom = '10%',
                ),
                
    #             opts.DataZoomOpts(
    #                 is_show=True, type_="inside", xaxis_index=0, range_end=100
    #             ),
    #             opts.DataZoomOpts(
    #                 is_show=True, type_="slider", xaxis_index=0, range_end=100
    #             ),
            ],
            axispointer_opts=opts.AxisPointerOpts(
                     is_show=True,
                     link=[{"xAxisIndex": "all"}],
                     label=opts.LabelOpts(background_color="#777"),
            ),
            tooltip_opts=opts.TooltipOpts(
                trigger="axis",
                axis_pointer_type="cross",
                background_color="rgba(245, 245, 245, 0.8)",
                border_width=1,
                border_color="#ccc",
                textstyle_opts=opts.TextStyleOpts(color="#000"),
            ),
        )
        .set_series_opts(
            label_opts=opts.LabelOpts(is_show=False),
        )
        .add_xaxis(agdata.index.tolist())
        .add_yaxis("XU1 Index",
                       agdata['XU1 Index'].tolist(),
                       is_smooth=True,
                       symbol_size=4,
                       yaxis_index=0,
                       linestyle_opts=opts.LineStyleOpts(color="black", width=1.2, ),
                       z_level=1,
                       markpoint_opts=opts.MarkPointOpts(
                           data=trade_series,
                           label_opts=opts.LabelOpts(
                               position="inside",
                               color="#fff",
                               font_size=9,
                            ),
                       ),
                   label_opts = opts.LabelOpts(is_show=False),
         )
        .add_yaxis("lm",
                       agdata['XU1 Index'].tolist(),
                       is_smooth=True,
                       symbol='none',
                       yaxis_index=0,
                       linestyle_opts=opts.LineStyleOpts(color="black", width=0.2, ),
                       z_level=1,
                       markpoint_opts=opts.MarkPointOpts(
                           data=lm_marker,
                           label_opts=opts.LabelOpts(
                               position="inside",
                               color="#fff",
                               font_size=9
                           ),
                       ),
                       tooltip_opts=opts.TooltipOpts(
                           is_show=False,
                        ),
                    )
        .add_yaxis("tj",
                       agdata['XU1 Index'].tolist(),
                       is_smooth=True,
                       symbol='none',
                       yaxis_index=0,
                       linestyle_opts=opts.LineStyleOpts(color="black", width=0.2, ),
                       z_level=1,
                       markpoint_opts=opts.MarkPointOpts(
                           data=tj_marker,
                           label_opts=opts.LabelOpts(
                               position="inside",
                               color="#fff",
                               font_size=9
                           ),
                       ),
                       tooltip_opts=opts.TooltipOpts(
                           is_show=False,
                        ),
                    )
        .add_yaxis("sy",
                       agdata['XU1 Index'].tolist(),
                       is_smooth=True,
                       symbol='none',
                       yaxis_index=0,
                       linestyle_opts=opts.LineStyleOpts(color="black", width=0.2, ),
                       z_level=1,
                       markpoint_opts=opts.MarkPointOpts(
                           data=sy_marker,
                           label_opts=opts.LabelOpts(
                               position="inside",
                               color="#fff",
                               font_size=9
                           ),
                       ),
                       tooltip_opts=opts.TooltipOpts(
                           is_show=False,
                       ),
                    )
        .add_yaxis("ty",
                       agdata['XU1 Index'].tolist(),
                       is_smooth=True,
                       symbol='none',
                       yaxis_index=0,
                       linestyle_opts=opts.LineStyleOpts(color="black", width=0.2, ),
                       z_level=1,
                       markpoint_opts=opts.MarkPointOpts(
                           data=ty_marker,
                           label_opts=opts.LabelOpts(
                               position="inside",
                               color="#fff",
                               font_size=9
                           ),
                       ),
                       tooltip_opts=opts.TooltipOpts(
                           is_show=False,
                       ),
                    )
        .add_yaxis("dy",
                       agdata['XU1 Index'].tolist(),
                       is_smooth=True,
                       symbol='none',
                       yaxis_index=0,
                       linestyle_opts=opts.LineStyleOpts(color="black", width=0.2, ),
                       z_level=1,
                       markpoint_opts=opts.MarkPointOpts(
                           data=dy_marker,
                           label_opts=opts.LabelOpts(
                               position="inside",
                               color="#fff",
                               font_size=9
                           ),
                       ),
                       tooltip_opts=opts.TooltipOpts(
                           is_show=False,
                       ),
                    )
        .add_yaxis("xx",
                       agdata['XU1 Index'].tolist(),
                       is_smooth=True,
                       symbol='none',
                       yaxis_index=0,
                       linestyle_opts=opts.LineStyleOpts(color="black", width=0.2, ),
                       z_level=1,
                       markpoint_opts=opts.MarkPointOpts(
                           data=xx_marker,
                           label_opts=opts.LabelOpts(
                               position="inside",
                               color="#fff",
                               font_size=9
                           ),
                       ),
                       tooltip_opts=opts.TooltipOpts(
                           is_show=False,
                       ),
                    )
        .add_yaxis("gxm",
                       agdata['XU1 Index'].tolist(),
                       is_smooth=True,
                       symbol='none',
                       yaxis_index=0,
                       linestyle_opts=opts.LineStyleOpts(color="black", width=0.2, ),
                       z_level=1,
                       markpoint_opts=opts.MarkPointOpts(
                           data=gxm_marker,
                           label_opts=opts.LabelOpts(
                               position="inside",
                               color="#fff",
                               font_size=9
                           ),
                       ),
                       tooltip_opts=opts.TooltipOpts(
                           is_show=False,
                       ),
                    )
            .add_yaxis("ting",
                       agdata['XU1 Index'].tolist(),
                       is_smooth=True,
                       symbol='none',
                       yaxis_index=0,
                       linestyle_opts=opts.LineStyleOpts(color="black", width=0.2, ),
                       z_level=1,
                       markpoint_opts=opts.MarkPointOpts(
                           data=ting_marker,
                           label_opts=opts.LabelOpts(
                               position="inside",
                               color="#fff",
                               font_size=9
                           ),
                       ),
                       tooltip_opts=opts.TooltipOpts(
                           is_show=False,
                       ),
                    )

        .add_yaxis("Upper",
                       agdata.Upper.values,
                       is_smooth=False,
                       symbol='none',
                       z_level=-1,
                       linestyle_opts=opts.LineStyleOpts(color="black", width=0.3),
                       areastyle_opts=opts.AreaStyleOpts(opacity=0.5, color='#FFCC99'),
                       label_opts = opts.LabelOpts(is_show=False),
                    )
        .add_yaxis("Lower",
                       agdata.Lower.values,
                       is_smooth=False,
                       symbol='none',
                       z_level=-1,
                       linestyle_opts=opts.LineStyleOpts(color="black", width=0.3),
                       areastyle_opts=opts.AreaStyleOpts(opacity=1, color='white'),
                       label_opts = opts.LabelOpts(is_show=False),
                    )

    )

    timeline = (
        Line(
        )
        .set_global_opts(
            xaxis_opts=opts.AxisOpts(
                type_="category",
                grid_index=1,
                axislabel_opts=opts.LabelOpts(is_show=False),
            ),
            yaxis_opts=opts.AxisOpts(
                name='Account',
                grid_index = 1,
                type_ = 'category',

            ),
           legend_opts = opts.LegendOpts(is_show = False)
        )
        .add_xaxis(xaxis_data = agdata.index.tolist())
        .add_yaxis("XU1 Index",
                   ['Theo' for x in agdata['XU1 Index']],
                   is_smooth=True,
                   symbol='none',
                   xaxis_index = 1,
                   yaxis_index = 1,
                   z_level=1,
                   label_opts=opts.LabelOpts(is_show=False),
                   linestyle_opts=opts.LineStyleOpts(color="black", width=0.1, ),
                   markpoint_opts=opts.MarkPointOpts(
                       data=trade_t,
                        label_opts=opts.LabelOpts(
                           position="inside",
                           color="#fff",
                           font_size=9
                       ),
                    ),
                   tooltip_opts=opts.TooltipOpts(
                       is_show=False,
                    ),
        )
        .add_yaxis("tj",
                       ['tj' for x in agdata['XU1 Index']],
                       is_smooth=True,
                       symbol='none',
                       xaxis_index = 1,
                       yaxis_index = 1,
                       linestyle_opts=opts.LineStyleOpts(color="black", width=0.1, ),
                       z_level=1,
                       markpoint_opts=opts.MarkPointOpts(
                           data=tj_t,
                           label_opts=opts.LabelOpts(
                               position="inside",
                               color="#fff",
                               font_size=9
                           ),
                       ),
                       tooltip_opts=opts.TooltipOpts(
                           is_show=False,
                        ),
                    )
            .add_yaxis("sy",
                       ['sy' for x in agdata['XU1 Index']],
                       is_smooth=True,
                       symbol='none',
                       xaxis_index = 1,
                       yaxis_index = 1,
                       linestyle_opts=opts.LineStyleOpts(color="black", width=0.1, ),
                       z_level=1,
                       markpoint_opts=opts.MarkPointOpts(
                           data=sy_t,
                           label_opts=opts.LabelOpts(
                               position="inside",
                               color="#fff",
                               font_size=9
                           ),
                       ),
                       tooltip_opts=opts.TooltipOpts(
                           is_show=False,
                       ),
                    )
            .add_yaxis("dy",
                       ['dy' for x in agdata['XU1 Index']],
                       is_smooth=True,
                       symbol='none',
                       xaxis_index = 1,
                       yaxis_index = 1,
                       linestyle_opts=opts.LineStyleOpts(color="black", width=0.1, ),
                       z_level=1,
                       markpoint_opts=opts.MarkPointOpts(
                           data=dy_t,
                           label_opts=opts.LabelOpts(
                               position="inside",
                               color="#fff",
                               font_size=9
                           ),
                       ),
                       tooltip_opts=opts.TooltipOpts(
                           is_show=False,
                        ),
                    )
            .add_yaxis("ty",
                       ['ty' for x in agdata['XU1 Index']],
                       is_smooth=True,
                       symbol='none',
                       xaxis_index = 1,
                       yaxis_index = 1,
                       linestyle_opts=opts.LineStyleOpts(color="black", width=0.1, ),
                       z_level=1,
                       markpoint_opts=opts.MarkPointOpts(
                           data=ty_t,
                           label_opts=opts.LabelOpts(
                               position="inside",
                               color="#fff",
                               font_size=9
                           ),
                       ),
                       tooltip_opts=opts.TooltipOpts(
                           is_show=False,
                        ),
                    )
            .add_yaxis("xx",
                       ['xx' for x in agdata['XU1 Index']],
                       is_smooth=True,
                       symbol='none',
                       xaxis_index = 1,
                       yaxis_index = 1,
                       linestyle_opts=opts.LineStyleOpts(color="black", width=0.1, ),
                       z_level=1,
                       markpoint_opts=opts.MarkPointOpts(
                           data=xx_t,
                           label_opts=opts.LabelOpts(
                               position="inside",
                               color="#fff",
                               font_size=9
                           ),
                       ),
                       tooltip_opts=opts.TooltipOpts(
                           is_show=False,
                        ),
                    )
            .add_yaxis("gxm",
                       ['gxm' for x in agdata['XU1 Index']],
                       is_smooth=True,
                       symbol='none',
                       xaxis_index = 1,
                       yaxis_index = 1,
                       linestyle_opts=opts.LineStyleOpts(color="black", width=0.1, ),
                       z_level=1,
                       markpoint_opts=opts.MarkPointOpts(
                           data=gxm_t,
                           label_opts=opts.LabelOpts(
                               position="inside",
                               color="#fff",
                               font_size=9
                           ),
                       ),
                       tooltip_opts=opts.TooltipOpts(
                           is_show=False,
                        ),
                    )
            .add_yaxis("ting",
                       ['ting' for x in agdata['XU1 Index']],
                       is_smooth=True,
                       symbol='none',
                       xaxis_index = 1,
                       yaxis_index = 1,
                       linestyle_opts=opts.LineStyleOpts(color="black", width=0.1, ),
                       z_level=1,
                       markpoint_opts=opts.MarkPointOpts(
                           data=ting_t,
                           label_opts=opts.LabelOpts(
                               position="inside",
                               color="#fff",
                               font_size=9
                           ),
                       ),
                       tooltip_opts=opts.TooltipOpts(
                           is_show=False,
                        ),
                    )

    )

    grid_chart = (
        Grid(init_opts=opts.InitOpts(width="1400px", height="800px") )
        .add(
                a50_line,
                grid_opts=opts.GridOpts(
                    pos_left="5%", pos_right="1%", pos_top="10%", height="50%"
                ),
            )
        .add(
                timeline,
                grid_opts=opts.GridOpts(
                    pos_left="5%", pos_right="1%", pos_top="63%", height="25%"
                ),
            )
    )
    return (grid_chart,base)

def if_trading_chart(d,b):
    dates = pd.date_range(start=d,end='2021-03-01').strftime("%Y-%m-%d")
    tl = Tab( )
    for d in dates:
        if os.path.exists('.\\股指数据\\'+d+'.xlsx'):
            print(d)
            (g,b) = if_get_grid(d,b)
            g.render('.\\交易日志\\0120.html')
            tl.add(g,d)
    tl.render('.\\templates\\IF_Log.html') 
    return tl

if __name__ == '__main__':
    if_trading_chart()