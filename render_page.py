import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import pyecharts.options as opts
from pyecharts.charts import Bar, Grid, Line, Liquid, Page, Pie, Timeline, Tab
from pyecharts.faker import Faker
import os
from trade_ih import ih_trading_chart, ih_get_grid
from trade_if import if_trading_chart, if_get_grid


def seperate_charts(d):
    page = Page(layout=Page.SimplePageLayout)
    page.add(
        ih_get_grid(d),
        if_get_grid(d),
    )
    return page

def page_simple_layout(d):
    page = Page(layout=Page.SimplePageLayout)
    (ihgrid,ih_base) = ih_get_grid(d,-20)
    (ifgrid,if_base) = if_get_grid(d,-20)

    page.add(
        ihgrid,
        ifgrid,
    )
    return page


def tab_pages(d):
    dates = pd.date_range(start=d, end='2021-03-01').strftime("%Y-%m-%d")
    tl = Tab()
    for d in dates:
        if os.path.exists('.\\股指数据\\' + d + '.xlsx'):
            p = page_simple_layout(d)
            tl.add(p, d)
    tl.render('.\\templates\\res.html')
    return tl

if __name__ == "__main__":
    page_simple_layout('2021-01-22').render('.\\templates\\d.html')
    # tab_pages('2021-01-21')
