from re import search

from dash import Dash, dcc, html, Input, Output
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Load your data into plot_df
plot_df = pd.read_parquet("depth_vs_breadth_plot_df.parquet", engine='pyarrow')

app = Dash(__name__)

# app.layout = html.Div([
#     html.H2("Depth vs Breadth for commanders based on last two years of deck updates", style={'fontFamily': 'Arial'}),
#     dcc.Input(
#         id='search',
#         type='text',
#         placeholder='Search commander...',
#         style={'padding': '8px', 'width': '300px', 'fontSize': '14px', 'fontFamily': 'Arial'}
#     ),
#     dcc.Graph(id='scatter', style={'height': '800px'})
# ])


app.layout = html.Div([
    html.H2("Breadth (x) vs Depth (y) of commanders based on history of deck updates", style={'fontFamily': 'Arial'}),
    html.P("This graphic shows the relationship between: X = breadth (number of users with a deck for this commander) and Y = depth (average number of updates for this commander across users after 60 days since deck creation)", style={'fontFamily': 'Arial'}),
    html.P("The color of the points indicates how long ago the commander was released, with a cap at 2 years. Use the dropdown to highlight specific commanders.", style={'fontFamily': 'Arial'}),
    html.P("Commanders with less than 200 users are not included.", style={'fontFamily': 'Arial'}),
    dcc.Dropdown(
        id='commander-select',
        options=[{'label': c, 'value': c} for c in sorted(plot_df['commanders'].dropna().unique())],
        value=[],
        multi=True,
        placeholder='Select commanders to highlight...',
        style={'width': '800px', 'fontSize': '14px', 'fontFamily': 'Arial'}
    ),
    dcc.Graph(id='scatter', style={'height': '800px'})
])

# calculate once outside callback
cmin = plot_df['time_since_release'].min()
cmax = plot_df['time_since_release'].max()

@app.callback(Output('scatter', 'figure'), Input('commander-select', 'value'))
def update_figure(selected_commanders):
    if not selected_commanders:
        matched = plot_df
        unmatched = pd.DataFrame()
    else:
        matched = plot_df[plot_df['commanders'].isin(selected_commanders)]
        unmatched = plot_df[~plot_df['commanders'].isin(selected_commanders)]

    marker_base = dict(
        colorscale=px.colors.sequential.thermal[::-1],
        cmin=cmin,
        cmax=cmax,
        size=8,
    )

    fig = go.Figure()

    # non-matching points - no hover
    if not unmatched.empty:
        fig.add_trace(go.Scatter(
            x=unmatched['num_users'],
            y=unmatched['average_num_updates'],
            mode='markers',
            marker=dict(
                **marker_base,
                color=unmatched['time_since_release'],
                opacity=0.1,
            ),
            hoverinfo='skip',
            showlegend=False,
        ))

    # matching points - with hover
    fig.add_trace(go.Scatter(
        x=matched['num_users'],
        y=matched['average_num_updates'],
        mode='markers',
        marker=dict(
            **marker_base,
            color=matched['time_since_release'],
            colorbar=dict(title='days since commander release (2 year cap)'),
            opacity=0.8,
        ),
        text=matched['commanders'],
        hovertemplate='<b>%{text}</b><br># users: %{x:,.0f}<br>avg updates: %{y:.3f}<extra></extra>',
        showlegend=False,
    ))

    fig.update_layout(
        title='Depth vs breadth of commanders',
        xaxis=dict(title='Breadth = # users with a deck for this commander (log scale)', type='log'),
        yaxis=dict(title='Depth = average deck updates for this commander across users'),
    )


    return fig

server = app.server

if __name__ == '__main__':
    app.run(debug=True)