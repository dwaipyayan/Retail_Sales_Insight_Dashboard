import pandas as pd
import numpy as np
import json


# Load data
path = 'cleaned data.csv'
df = pd.read_csv(path, encoding='ISO-8859-1')

# Basic cleaning and typing
for col in ['Sales','Profit','Quantity','Discount']:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

# Parse dates (day-first ambiguous in sample). Try both formats safely.
# We will coerce and drop NaT later only for time series aggregations.
order_date = pd.to_datetime(df['Order Date'], errors='coerce', format="%d/%m/%Y")
if order_date.isna().mean() > 0.5:
    order_date = pd.to_datetime(df['Order Date'], errors='coerce', dayfirst=False)

df['Order_Date_parsed'] = order_date

# Derived time columns
df['Year'] = df['Order_Date_parsed'].dt.year
df['Month'] = df['Order_Date_parsed'].dt.to_period('M').dt.to_timestamp()

# Filter rows with valid dates for time-series
ts = df.dropna(subset=['Order_Date_parsed']).copy()

# 1) Monthly Sales & Profit
monthly = ts.groupby('Month').agg({'Sales':'sum','Profit':'sum'}).sort_index().reset_index()
monthly_x = [m.strftime('%Y-%m') for m in monthly['Month']]
monthly_sales = [float(x) for x in monthly['Sales'].fillna(0.0).values]
monthly_profit = [float(x) for x in monthly['Profit'].fillna(0.0).values]

# 2) Category Sales
cat = df.groupby('Category', dropna=False)['Sales'].sum().sort_values(ascending=False).reset_index()
cat_labels = [str(x) for x in cat['Category'].fillna('Unknown').values]
cat_sales = [float(x) for x in cat['Sales'].fillna(0.0).values]

# 3) Sub-Category Top 10 by Sales
sub = df.groupby('Sub-Category', dropna=False)['Sales'].sum().sort_values(ascending=False).head(10).reset_index()
sub_labels = [str(x) for x in sub['Sub-Category'].fillna('Unknown').values]
sub_sales = [float(x) for x in sub['Sales'].fillna(0.0).values]

# 4) Region Sales
region = df.groupby('Region', dropna=False)['Sales'].sum().sort_values(ascending=False).reset_index()
region_labels = [str(x) for x in region['Region'].fillna('Unknown').values]
region_sales = [float(x) for x in region['Sales'].fillna(0.0).values]

# 5) Top 10 States by Sales (if State exists)
if 'State' in df.columns:
    state = df.groupby('State', dropna=False)['Sales'].sum().sort_values(ascending=False).head(10).reset_index()
    state_labels = [str(x) for x in state['State'].fillna('Unknown').values]
    state_sales = [float(x) for x in state['Sales'].fillna(0.0).values]
else:
    state_labels = []
    state_sales = []

# Quick insights
total_sales = float(df['Sales'].fillna(0.0).sum())
total_profit = float(df['Profit'].fillna(0.0).sum())
if len(cat) > 0:
    top_cat = str(cat.iloc[0]['Category'])
else:
    top_cat = 'N/A'

insights = [
    'Total Sales: ' + str(round(total_sales, 2)),
    'Total Profit: ' + str(round(total_profit, 2)),
    'Top Category by Sales: ' + top_cat
]

# Bundle data for JS
js_data = {
    'monthly_x': monthly_x,
    'monthly_sales': monthly_sales,
    'monthly_profit': monthly_profit,
    'cat_labels': cat_labels,
    'cat_sales': cat_sales,
    'sub_labels': sub_labels,
    'sub_sales': sub_sales,
    'region_labels': region_labels,
    'region_sales': region_sales,
    'state_labels': state_labels,
    'state_sales': state_sales,
    'insights': insights
}

payload = json.dumps(js_data)

# Build HTML with placeholders then replace once to avoid .format issues with CSS vars
html_template = (
    "<link rel=stylesheet href=https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap>" +
    "<script src=https://cdn.jsdelivr.net/npm/apexcharts></script>" +
    "<style>" +
    ":root{--bg:#0b1020;--panel:#121832;--text:#e6e8ef;--muted:#9aa4bc;--accent:#7c5cff;--grid:#1f2747}" +
    "body{font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;background:var(--bg);color:var(--text)}" +
    ".wrap{max-width:1200px;margin:0 auto;padding:20px}" +
    ".title{font-size:26px;font-weight:700;margin:8px 0 4px 0}" +
    ".subtitle{color:var(--muted);font-size:14px;margin-bottom:18px}" +
    ".insights{background:var(--panel);border:1px solid var(--grid);border-radius:10px;padding:14px 16px;margin:10px 0 18px 0}" +
    ".grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}" +
    ".card{background:var(--panel);border:1px solid var(--grid);border-radius:12px;padding:12px}" +
    ".card h3{font-size:18px;font-weight:600;margin:0 0 8px 0}" +
    ".hint{font-size:12px;color:var(--muted);margin:4px 0 10px 0}" +
    ".apexcharts-canvas{margin:0 auto}" +
    "@media(max-width:900px){.grid{grid-template-columns:1fr}}" +
    "</style>" +
    "<div class=wrap>" +
      "<div class=title>Sales Performance Overview</div>" +
      "<div class=subtitle>Interactive charts with zoom, pan, hover, brush and legend filtering</div>" +
      "<div class=insights id=insightsBox></div>" +
      "<div class=grid>" +
        "<div class=card><h3>Monthly Sales vs Profit</h3><div class=hint>Brush below to zoom the main chart</div><div id=chart_ts></div><div id=chart_brush style=margin-top:10px></div></div>" +
        "<div class=card><h3>Sales by Category</h3><div id=chart_category></div></div>" +
        "<div class=card><h3>Top 10 Sub-Categories</h3><div id=chart_subcat></div></div>" +
        "<div class=card><h3>Sales by Region</h3><div id=chart_region></div></div>" +
        "<div class=card><h3>Top 10 States by Sales</h3><div id=chart_state></div></div>" +
      "</div>" +
    "</div>" +
    "<script>" +
    "document.addEventListener('DOMContentLoaded', function(){" +
      "var data = __PAYLOAD__;" +
      "var colors = ['#7c5cff','#22c55e','#38bdf8','#f59e0b','#ef4444','#a78bfa','#14b8a6'];" +
      "var insightsBox = document.getElementById('insightsBox');" +
      "if (Array.isArray(data.insights)) { insightsBox.innerHTML = '<ul style=margin:0;padding-left:18px>' + data.insights.map(function(x){return '<li>'+x+'</li>';}).join('') + '</ul>'; }" +

      # Time series main chart
      "var optionsTS = {" +
        "chart:{id:'mainTS',type:'line',height:300,background:'transparent',foreColor:'#e6e8ef',toolbar:{show:true,tools:{download:true,pan:true,zoom:true,zoomin:true,zoomout:true,reset:true}}}," +
        "series:[{name:'Sales',data:data.monthly_sales},{name:'Profit',data:data.monthly_profit}]," +
        "colors:[colors[0],colors[4]]," +
        "xaxis:{categories:data.monthly_x,labels:{style:{fontSize:'12px'}},title:{text:'Month',style:{fontSize:'14px',fontWeight:500}}}," +
        "yaxis:{labels:{style:{fontSize:'12px'}},title:{text:'Amount',style:{fontSize:'14px',fontWeight:500}}}," +
        "dataLabels:{enabled:false},legend:{show:true},grid:{borderColor:'#1f2747'},stroke:{curve:'smooth',width:2},responsive:[{breakpoint:600,options:{chart:{height:260}}}]" +
      "};" +
      "new ApexCharts(document.querySelector('#chart_ts'), optionsTS).render();" +

      # Brush chart
      "var optionsBrush = {" +
        "chart:{id:'brushTS',type:'area',height:120,brush:{target:'mainTS',enabled:true},selection:{enabled:true,fill:{color:'#7c5cff',opacity:0.1},xaxis:{}},background:'transparent',foreColor:'#e6e8ef'}," +
        "series:[{name:'Sales',data:data.monthly_sales}]," +
        "colors:[colors[0]]," +
        "xaxis:{categories:data.monthly_x,labels:{show:false}}," +
        "yaxis:{labels:{show:false}}," +
        "dataLabels:{enabled:false},legend:{show:false},grid:{borderColor:'#1f2747'},stroke:{curve:'smooth',width:1}" +
      "};" +
      "new ApexCharts(document.querySelector('#chart_brush'), optionsBrush).render();" +

      # Category chart
      "var optionsCat = {" +
        "chart:{type:'bar',height:300,background:'transparent',foreColor:'#e6e8ef',toolbar:{show:true}}," +
        "series:[{name:'Sales',data:data.cat_sales}]," +
        "colors:[colors[2]]," +
        "xaxis:{categories:data.cat_labels,labels:{rotate:-15,style:{fontSize:'12px'}},title:{text:'Category',style:{fontSize:'14px',fontWeight:500}}}," +
        "yaxis:{labels:{style:{fontSize:'12px'}},title:{text:'Sales',style:{fontSize:'14px',fontWeight:500}}}," +
        "dataLabels:{enabled:false},legend:{show:true},grid:{borderColor:'#1f2747'},responsive:[{breakpoint:600,options:{chart:{height:260}}}]" +
      "};" +
      "new ApexCharts(document.querySelector('#chart_category'), optionsCat).render();" +

      # Sub-category chart
      "var optionsSub = {" +
        "chart:{type:'bar',height:300,background:'transparent',foreColor:'#e6e8ef',toolbar:{show:true}}," +
        "series:[{name:'Sales',data:data.sub_sales}]," +
        "colors:[colors[3]]," +
        "xaxis:{categories:data.sub_labels,labels:{rotate:-25,style:{fontSize:'12px'}},title:{text:'Sub-Category',style:{fontSize:'14px',fontWeight:500}}}," +
        "yaxis:{labels:{style:{fontSize:'12px'}},title:{text:'Sales',style:{fontSize:'14px',fontWeight:500}}}," +
        "dataLabels:{enabled:false},legend:{show:true},grid:{borderColor:'#1f2747'},responsive:[{breakpoint:600,options:{chart:{height:260}}}]" +
      "};" +
      "new ApexCharts(document.querySelector('#chart_subcat'), optionsSub).render();" +

      # Region chart
      "var optionsRegion = {" +
        "chart:{type:'donut',height:300,background:'transparent',foreColor:'#e6e8ef',toolbar:{show:true}}," +
        "series:data.region_sales," +
        "labels:data.region_labels," +
        "colors:[colors[0],colors[1],colors[2],colors[3],colors[4],colors[5],colors[6]]," +
        "legend:{show:true},dataLabels:{enabled:true},grid:{borderColor:'#1f2747'},responsive:[{breakpoint:600,options:{chart:{height:260},legend:{position:'bottom'}}}]" +
      "};" +
      "new ApexCharts(document.querySelector('#chart_region'), optionsRegion).render();" +

      # State chart
      "var optionsState = {" +
        "chart:{type:'bar',height:300,background:'transparent',foreColor:'#e6e8ef',toolbar:{show:true}}," +
        "series:[{name:'Sales',data:data.state_sales}]," +
        "colors:[colors[5]]," +
        "xaxis:{categories:data.state_labels,labels:{rotate:-25,style:{fontSize:'12px'}},title:{text:'State',style:{fontSize:'14px',fontWeight:500}}}," +
        "yaxis:{labels:{style:{fontSize:'12px'}},title:{text:'Sales',style:{fontSize:'14px',fontWeight:500}}}," +
        "dataLabels:{enabled:false},legend:{show:true},grid:{borderColor:'#1f2747'},responsive:[{breakpoint:600,options:{chart:{height:260}}}]" +
      "};" +
      "new ApexCharts(document.querySelector('#chart_state'), optionsState).render();" +
    "});" +
    "</script>"
)

html_out = html_template.replace('__PAYLOAD__', payload)

with open("dashboard.html", "w", encoding="utf-8") as f:
    f.write(html_out)

print(" Dashboard saved as dashboard.html. Open it in your browser to view the dashboard.")
