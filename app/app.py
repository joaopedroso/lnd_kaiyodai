import sys
import pandas as pd

import os
import pathlib
import statistics

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import dash_table
import plotly.graph_objs as go
import dash_daq as daq
from dash.exceptions import PreventUpdate


DATADIR = '../data'
SRCDIR = '../src'
sys.path.insert(0, SRCDIR)
from mk_instances import mk_instance, read_data
from clustering import preclustering
from lnd import lnd_ms, lnd_ss, mk_costs


def jsonize(data):
    (weight, cust, plnt, dc, dc_lb, dc_ub, demand, plnt_ub, name, tp_cost, del_cost, dc_fc, dc_vc) = data
    dem_keys = list(demand.keys())  # transform demand[cust,prod] into serializable objects
    dem_values = list(demand.values())
    ub_keys = list(plnt_ub.keys())
    ub_values = list(plnt_ub.values())
    tp_cost_keys = list(tp_cost.keys())
    tp_cost_values = list(tp_cost.values())
    del_cost_keys = list(del_cost.keys())
    del_cost_values = list(del_cost.values())
    return (weight, cust, plnt, dc, dc_lb, dc_ub, dem_keys, dem_values, ub_keys, ub_values, name, \
            tp_cost_keys, tp_cost_values, del_cost_keys, del_cost_values, dc_fc, dc_vc)


def unjsonize(data):
    (weight, cust, plnt, dc, dc_lb, dc_ub, dem_keys, dem_values, ub_keys, ub_values, name, \
     tp_cost_keys, tp_cost_values, del_cost_keys, del_cost_values, dc_fc, dc_vc) = data
    demand = {(c,p):dem for ((c,p),dem) in zip(dem_keys, dem_values)}
    plnt_ub = {(z,p):ub for ((z,p),ub) in zip(ub_keys, ub_values)}
    tp_cost = {(i,j):cost for ((i,j),cost) in zip(tp_cost_keys, tp_cost_values)}
    del_cost = {(i,j):cost for ((i,j),cost) in zip(del_cost_keys, del_cost_values)}
    return (weight, cust, plnt, dc, dc_lb, dc_ub, demand, plnt_ub, name, tp_cost, del_cost, dc_fc, dc_vc)


def mk_data(n_plants=3, n_dcs=100, n_custs=100, n_prods=5, seed=1):
    df = read_data()
    (weight, cust, plnt, dc, dc_lb, dc_ub, demand, plnt_ub, name) = \
        mk_instance(df, n_plants, n_dcs, n_custs, n_prods, seed)
    (tp_cost, del_cost, dc_fc, dc_vc) = mk_costs(plnt, dc, cust)

    data = (weight, cust, plnt, dc, dc_lb, dc_ub, demand, plnt_ub, name, tp_cost, del_cost, dc_fc, dc_vc)
    return data


def solve_lnd(data, cluster_dc, dc_num, model="multiple souce"):

    (weight, cust, plnt, dc, dc_lb, dc_ub, demand, plnt_ub, name, tp_cost, del_cost, dc_fc, dc_vc) = data
    
    prods = weight.keys()
    models = {
        "multiple source":lnd_ms,
        "single source":lnd_ss
    }
    k = list(models.keys())[0]
    TIME_LIM = 300 # allow gurobi to use 5 minutes
    print(f"*** new instance, {len(plnt)} plants + {len(dc)} dc's + {len(cust)} customers ***")
    print(f"***** dc's clustered into {len(cluster_dc)} groups, for choosing {dc_num} dc's")
    print(f"* using {k} model *")
    model = models[k](weight, cust, cluster_dc, dc_lb, dc_ub, plnt, plnt_ub,
                      demand, tp_cost, del_cost, dc_fc, dc_vc, dc_num)
    model.setParam('TimeLimit', TIME_LIM)
    model.optimize()
    # model.write("lnd.lp")
     
    EPS = 1.e-6
    for x in model.getVars():
        if x.X > EPS:
            print(x.varName, x.X)

    x,y = model.__data

    dcs = [i for i in cluster_dc if y[i].X > .5]
    print("solution:", dcs)
    return dcs


# data = mk_data(n_plants=3, n_dcs=100, n_custs=100, n_prods=5, seed=1)
# solve_lnd(data)
# exit(0)
    


app = dash.Dash(
    __name__,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)
server = app.server
app.config["suppress_callback_exceptions"] = True

APP_PATH = str(pathlib.Path(__file__).parent.resolve())
##### df = pd.read_csv(os.path.join(APP_PATH, os.path.join("data", "spc_data.csv")))

# mapbox
mapbox_access_token = "pk.eyJ1IjoieWNhb2tyaXMiLCJhIjoiY2p1MDR5c3JmMzJsbjQ1cGlhNHA3MHFkaCJ9.xb3lXp5JskCYFewsv5uU1w"

def build_banner():
    return html.Div(
        id="banner",
        className="banner",
        children=[
            html.Div(
                id="banner-text",
                children=[
                    html.H5("Facility location module"),
                    html.P("Optimization for Supply Chain Management, "
                           "Tokyo University of Marine Science and Technology"),
                ],
            ),
            html.Div(
                id="banner-logo",
                children=[
                    html.Img(id="logo", src=app.get_asset_url("tumsat.png")),
                ],
            ),
            html.Div(
                children=[
                    html.Button(
                        id="learn-more-button", children="LEARN MORE", n_clicks=0
                    ),
                ],
            ),
        ],
    )


def build_tabs():
    return html.Div(
        id="tabs",
        className="tabs",
        children=[
            dcc.Tabs(
                id="app-tabs",
                value="tab1",
                className="custom-tabs",
                children=[
                    dcc.Tab(
                        id="Specs-tab",
                        label="Data Source Settings",
                        value="tab1",
                        className="custom-tab",
                        selected_className="custom-tab--selected",
                    ),
                    dcc.Tab(
                        id="Control-chart-tab",
                        label="Optimization Dashboard",
                        value="tab2",
                        className="custom-tab",
                        selected_className="custom-tab--selected",
                    ),
                ],
            )
        ],
    )


##### def init_df():
#####     return {}
#####  
##### state_dict = init_df()
##### def init_value_setter_store():
#####     # Initialize store data
#####     state_dict = init_df()
#####     return state_dict

access_data = (
    # (id, description, type, shadowed text)
    ("folder-name", "Enter URL for the data folder", "text", "url", "https://raw.githubusercontent.com/joaopedroso/kaiyodai/master/DATA/random-instance/"),
    ("user-name", "Enter user name", "text", "user name", "joaopedroso"),
    ("password", "Enter password", "password", "", ""),
    )
access_data = (
    # (id, description, type, shadowed text)
    ("n_plants-name", "Enter number of plants",         "number", "n_plants", 3),
    ("n_dcs-name",    "Number of distribution centers", "number", "n_dcs",    100),
    ("n_custs-name",  "Number of customers",            "number", "n_custs",  250),
    ("n_prods-name",  "Number of products",             "number", "n_prods",  5),
    ("seed-name",     "Seed for random generator",      "number", "seed",     1),
    )
access_children = [ (html.Label(id="label-".format(dtid), children=dtdesc),
                    dcc.Input(id=dtid, type=dttype, placeholder=dthldr, value=dtval),
                    html.Br()) for (dtid, dtdesc, dttype, dthldr, dtval) in access_data]
access_children = [item for sublist in access_children for item in sublist]


def build_tab_1():
    return [
        # Manually select data sources
        html.Div(
            id="set-specs-intro-container",
            # className='twelve columns',
            children=html.P(
                # "Specify data sources and access credentials here."
                "Specify parameters for data preparation here."
            ),
        ),
        html.Div(
            id="settings-menu",
            children=[
                html.Div(
                    id="input-sources",
                    # className='five columns',
                    children=access_children,
                ),
                html.Div(
                    className='one column',
                ),
                html.Div(
                    id="current-data-summary",
                    # className='five columns',
                    children=[
                        dcc.Loading(
                            id="loading-2",
                            children=[html.Div([html.Div(id="loading-output-2")])],
                            type="circle",
                        ),
                        html.Label(id="products-summary"),
                    ],
                ),
                html.Div(
                    id="value-setter-menu",
                    # className='six columns',
                    children=[
                        html.Div(id="value-setter-panel"),
                        html.Br(),
                        html.Div(
                            id="button-div",
                            children=[
                                html.Button("Update", id="value-setter-set-btn"),
                            ],
                        ),
                        html.Div(
                            id="value-setter-view-output", className="output-datatable"
                        ),
                    ],
                ),
            ],
        ),
    ]

def build_tab_2():
    return [
        # Manually select data sources
        html.Div(
            id="status-container",
            className='twelve columns',
            children=[
                html.Div(
                    id="quick-stats",
                    className="five columns",
                    children=[
                        build_instructions()
                    ],
                ),
                html.Div(
                    id="# commentl-graph",
                    className="seven columns",
                    children=[
                        build_graph(),
                    ],
                ),
            ],
        ),
    ]


def generate_modal():
    return html.Div(
        id="markdown",
        className="modal",
        children=(
            html.Div(
                id="markdown-container",
                className="markdown-container",
                children=[
                    html.Div(
                        className="close-container",
                        children=html.Button(
                            "Close",
                            id="markdown_close",
                            n_clicks=0,
                            className="closeButton",
                        ),
                    ),
                    html.Div(
                        className="markdown-text",
                        children=dcc.Markdown(
                            children=(
                                """
                        ###### About this app

                        A decision support tool for network logistics design / facility location.

                        ###### How to use this app

                        To be completed:

                        1. Instantiate data
                        2. Select potential places for facilities
                        3. Set parameters (number of facilities, ...)
                        4. Optimize the problem
                    """
                            )
                        ),
                    ),
                ],
            )
        ),
    )


app.layout = html.Div(
    id="big-app-container",
    children=[
        build_banner(),
        html.Div(
            id="app-container",
            children=[
                build_tabs(),
                # Main app
                html.Div(id="app-content"),
            ],
        ),
        dcc.Store(id="data-store", data=None),
        dcc.Store(id="inst-pars-store", data=None, storage_type='session'),
        # dcc.Store(id="csv-source-store", data=None, storage_type='session'),
        html.Div(id="output"),
        generate_modal(),
    ],
)

def build_instructions():
    return html.Div(
        id="left-col",
        children=[
            html.P(className="instructions", children="Select candidates"),
            html.Div(
                id="choose-nclusters",
                children=[
                    html.Label("Number of clusters:", className="eight columns", style={'color': 'orange'}),
                    html.Div(
                        daq.NumericInput(id="nclusters", className="setting-input", size=100, max=10000, value=50),
                        className="three columns", style={'color': 'green'}
                    ),
                ],
                className="row",
            ),
            html.Div(
                id="choose-ndcs",
                children=[
                    html.Label("Number of DCs to open:", className="eight columns", style={'color': 'orange'}),
                    html.Div(
                        daq.NumericInput(id="ndcs", className="setting-input", size=100, max=10000, value=5),
                        className="three columns", style={'color': 'green'}
                    ),
                ],
                className="row",
            ),
            dcc.Dropdown(
                id="operator-select",
                options=[
                    {"label": i, "value": i}
                    for i in [1,2,3]
                ],
                multi=True,
                value=[1,2],
            ),
            html.Div(
                html.Button("Cluster and optimize", id="update-DCs", style={'color': 'white'}),
            ),
            html.Label(id="products-summary-2"),
        ],
    )

def build_graph():
    return html.Div(
        id="right-col",
        children=[
            html.Div(
                id="map-container",
                children=[
                    html.P(className="instructions", children="Customer map"),
                    dcc.Graph(
                        id="dc-map",
                        figure={
                            "layout": {
                                "paper_bgcolor": "#192444",
                                "plot_bgcolor": "#192444",
                            }
                        },
                        config={"scrollZoom": True, "displayModeBar": True},
                    ),
                ],
            ),
            # END
            html.Div(
                id="ternary-map-container",
                children="end here",
            ),
        ],
    )




@app.callback(
    Output("app-content", "children"),
    [Input("app-tabs", "value")]
)
def render_tab_content(tab_switch):
    if tab_switch == "tab1":
        return build_tab_1()
    return build_tab_2()


# ====== Callbacks to update stored data via click =====
# add a click to the appropriate store.
# [jpp: ] copied from Dash Core Components documentation
### @app.callback(Output("csv-source-store", "data"),
###               [Input("value-setter-set-btn", "n_clicks")],
###               [State("folder-name", "value"),
###                State("user-name", "value"),
###                State("password", "value"),
###               ])
### def setup_csv_sources(n_clicks, folder, user, password):
###     if n_clicks is None:
###         # prevent the None callbacks is important with the store component.
###         # you don't want to update the store for nothing.
###         raise PreventUpdate
###  
###     data = {}
###     data["folder"] = folder
###     data["user"] = user
###     data["password"] = password
###     return data


@app.callback(Output("inst-pars-store", "data"),
              [Input("value-setter-set-btn", "n_clicks")],
              [State("n_plants-name", "value"),
               State("n_dcs-name",    "value"),
               State("n_custs-name",  "value"),
               State("n_prods-name",  "value"),
               State("seed-name",     "value"),
              ])
def setup_inst_parameters(n_clicks, n_plants, n_dcs, n_custs, n_prods, seed):
    if n_clicks is None:
        # prevent the None callbacks is important with the store component.
        # you don't want to update the store for nothing.
        raise PreventUpdate

    data = {}
    data["n_plants"] = n_plants
    data["n_dcs"   ] = n_dcs   
    data["n_custs" ] = n_custs 
    data["n_prods" ] = n_prods 
    data["seed"    ] = seed
    return data


### from data_from_url import data_from_url
### @app.callback([Output("loading-output-2", "children"),Output("data-store", "data")],
###               [Input("value-setter-set-btn", "n_clicks")],
###               [State("csv-source-store", "data")])
### def init_data__(n_clicks, csv_src):
###     print("no explanation")
###     if n_clicks is None:
###         raise PreventUpdate
###  
###     # DIR = "https://raw.githubusercontent.com/joaopedroso/kaiyodai/master/DATA/random-instance/"
###     # username = "joaopedroso"
###     # password = ""
###     if csv_src is None:
###         return None
###     DIR = csv_src["folder"]
###     username = csv_src["user"]
###     password = csv_src["password"]
###     if DIR is None or username is None or password is None:
###         return None
###  
###     try:
###         (weight, cust, plnt, dc, dc_lb, dc_ub, demand, plnt_ub) = data_from_url(DIR, username, password)
###         dem_keys = list(demand.keys())      # transform demand[cust,prod] into serializable objects
###         dem_values = list(demand.values())
###         ub_keys = list(plnt_ub.keys())
###         ub_values = list(plnt_ub.values())
###         return 'Data in {}'.format(DIR), (weight, cust, plnt, dc, dc_lb, dc_ub, dem_keys, dem_values, ub_keys, ub_values)
###     except:
###         return '____No data stored', None


@app.callback([Output("loading-output-2", "children"), Output("data-store", "data")],
              [Input("value-setter-set-btn", "n_clicks")],
              [State("inst-pars-store", "data")]
              # [State("n_plants", "value"),
              #  State("n_dcs",  "value"),
              #  State("n_custs",        "value"),
              #  State("n_prods",        "value"),
              #  State("seed",   "value"),
              # ]
              )
def init_data(n_clicks,  inst_data):
    if n_clicks is None:
        raise PreventUpdate

    if inst_data is None:
        return 'No data stored', None

    n_plants = inst_data["n_plants"] 
    n_dcs    = inst_data["n_dcs"   ] 
    n_custs  = inst_data["n_custs" ] 
    n_prods  = inst_data["n_prods" ] 
    seed     = inst_data["seed"    ] 
    if n_plants is None or n_dcs is None or n_custs is None or n_prods is None or seed is None:
        return "incomplete form, please fill values", None

    try:
        data = mk_data(n_plants, n_dcs, n_custs, n_prods, seed)
        jdata = jsonize(data)
        return f'Data in created from {inst_data}', jdata
    except:
        return 'No data could be prepared', None


### import time
### @app.callback(Output("loading-output-2", "children"),
###               [Input("value-setter-set-btn", "n_clicks")],
###               [State("csv-source-store", "data")])
### def input_triggers_nested(value, data):
###     if data is None:
###         return 'No data stored'
###     
###     return 'CSV data stored: {} '.format(data)
@app.callback(
    Output("products-summary", "children"),
    [Input("data-store", "data")],
)
def update_summary(data):
    if data is None:
        return 'No data stored'
    
    # (weight, cust, plnt, dc, dc_lb, dc_ub, dem_keys, dem_values, ub_keys, ub_values) = data
    (weight, cust, plnt, dc, dc_lb, dc_ub, dem_keys, dem_values, ub_keys, ub_values, name, \
     tp_cost_keys, tp_cost_values, del_cost_keys, del_cost_values, dc_fc, dc_vc) = data
    # demand = dict(zip(dem_keys, dem_values))
    plnt_ub = {(plnt,prod):ub for ((plnt,prod),ub) in zip(ub_keys, ub_values)}
    return 'Current data stored: {} plants, {} customers, {} products'.format(len(plnt), len(cust), len(weight))
    
@app.callback(
    Output("products-summary-2", "children"),
    [Input("data-store", "data")],
)
def update_summary_2(data):
    if data is None:
        return 'No data stored ... {}'.format(data)
    
    # (weight, cust, plnt, dc, dc_lb, dc_ub, dem_keys, dem_values, ub_keys, ub_values) = data
    (weight, cust, plnt, dc, dc_lb, dc_ub, dem_keys, dem_values, ub_keys, ub_values, name, \
     tp_cost_keys, tp_cost_values, del_cost_keys, del_cost_values, dc_fc, dc_vc) = data
    plnt_ub = {(plnt,prod):ub for ((plnt,prod),ub) in zip(ub_keys, ub_values)}
    return 'Current data stored: {} plants, {} customers, {} products'.format(len(plnt), len(cust), len(weight))
    


@app.callback(
    Output("dc-map", "figure"),
    [Input("update-DCs", "n_clicks")],
    [State("data-store", "data"), State("nclusters", "value"), State("ndcs", "value")],
)
def update_graph(n_clicks, data, n_clusters, n_dcs):
    if n_clicks is None or data is None:
        raise PreventUpdate

    data = unjsonize(data)
    (weight, cust, plnt, dc, dc_lb, dc_ub, demand, plnt_ub, name, tp_cost, del_cost, dc_fc, dc_vc) = data

    lats, lons = zip(*[cust[i] for i in cust])
    lat_center = statistics.mean(lats)
    lon_center = statistics.mean(lons)
    dc_lats, dc_lons = zip(*[dc[i] for i in dc])
    p_lats, p_lons = zip(*[plnt[i] for i in plnt])


    # clustering part
    print(f'clustering {n_clusters}...')
    prods = weight.keys()
    cluster_dc = preclustering(cust, dc, prods, demand, n_clusters)
    cdc_lats, cdc_lons = zip(*[dc[i] for i in cluster_dc])
    print("cluster_dc:", cluster_dc)
    print("done.")

    # optimization part
    print(f'optimizing {n_dcs}...')
    opt_dc = solve_lnd(data, cluster_dc, n_dcs)
    odc_lats, odc_lons = zip(*[dc[i] for i in opt_dc])
    print("opt_dc:", opt_dc)
    print("done.")


    

    layout = go.Layout(
        clickmode="event+select",
        dragmode="pan",
        showlegend=True,
        autosize=True,
        hovermode="closest",
        margin=dict(l=0, r=0, t=0, b=0),
        mapbox=go.layout.Mapbox(
            accesstoken=mapbox_access_token,
            bearing=0,
            center=go.layout.mapbox.Center(lat=lat_center, lon=lon_center),
            pitch=0,
            zoom=3.8,
            style='dark',
        ),
        legend=dict(
            bgcolor="#1f2c56",
            orientation="h",
            font=dict(color="white"),
            x=0,
            y=0,
            yanchor="bottom",
        ),
    )
    pnts = [
        go.Scattermapbox(
            lat=p_lats,
            lon=p_lons,
            text=[i for i in plnt],
            mode="markers",
            marker={"color": "white", "size": 10, "opacity": .9},
            name="Plant",
            # selectedpoints=selected_index,
            # customdata=text,
        ),
        go.Scattermapbox(
            lat=lats,
            lon=lons,
            text=[i for i in cust],
            mode="markers",
            marker={"color": "white", "size": 3, "opacity": 1.},
            name="Customer",
            # selectedpoints=selected_index,
            # customdata=text,
        ),
        go.Scattermapbox(
            lat=dc_lats,
            lon=dc_lons,
            text=[i for i in dc],
            mode="markers",
            marker={"color": "green", "size": 5, "opacity": 0.9},
            name="DC",
            # selectedpoints=selected_index,
            # customdata=text,
        ),
        go.Scattermapbox(
            lat=cdc_lats,
            lon=cdc_lons,
            text=[i for i in cluster_dc],
            mode="markers",
            marker={"color": "orange", "size": 7, "opacity": 0.9},
            name="DC-clustered",
            # selectedpoints=selected_index,
            # customdata=text,
        ),
        go.Scattermapbox(
            lat=odc_lats,
            lon=odc_lons,
            text=[i for i in opt_dc],
            mode="markers",
            marker={"color": "yellow", "size": 9, "opacity": 0.9},
            name="Optimum DCs",
            # selectedpoints=selected_index,
            # customdata=text,
        ),
    ]
    return {"data": pnts, "layout": layout}



# @app.callback(
#     Output("output", "children"),
#     [Input("value-setter-set-btn", "n_clicks")],
#     [
#         State("folder-name", "value"),
#         State("user-name", "value"),
#         State("password", "value"),
#         State("data-store", "data"),
#     ],
# )
# def update_output(n_clicks, folder, user, password, data):
#     # just for debugging
#     size = -1 if data is None else len(data)
#     return u'*** {} *** Folder: {} -- Username: {} -- Password {}'.format(size, folder, user, password)
    

# ======= Callbacks for modal popup ======= [jpp OK]
@app.callback(
    Output("markdown", "style"),
    [Input("learn-more-button", "n_clicks"), Input("markdown_close", "n_clicks")],
)
def update_click_output(button_click, close_click):
    ctx = dash.callback_context

    if ctx.triggered:
        prop_id = ctx.triggered[0]["prop_id"].split(".")[0]
        if prop_id == "learn-more-button":
            return {"display": "block"}

    return {"display": "none"}



# Running the server
if __name__ == "__main__":
    app.run_server(debug=True, port=8050)
