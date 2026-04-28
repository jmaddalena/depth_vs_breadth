from dash import Dash, dcc, html, Input, Output
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Load your data into plot_df
plot_df = pd.read_parquet("depth_vs_breadth_plot_df.parquet", engine='pyarrow')

app = Dash(__name__)

app.layout = html.Div([
    html.H2("Depth vs Breadth for commanders based on last two years of deck updates", style={'fontFamily': 'Arial'}),
    dcc.Input(
        id='search',
        type='text',
        placeholder='Search commander...',
        style={'padding': '8px', 'width': '300px', 'fontSize': '14px', 'fontFamily': 'Arial'}
    ),
    dcc.Graph(id='scatter', style={'height': '800px'})
])

@app.callback(Output('scatter', 'figure'), Input('search', 'value'))
def update_figure(search):
    if not search:
        plot_df['match'] = True
    else:
        plot_df['match'] = plot_df['commanders'].str.lower().str.contains(search.lower(), na=False)

    fig = go.Figure()

    if not search:
        matched = plot_df
        unmatched = pd.DataFrame()
    else:
        matched = plot_df[plot_df['match']]
        unmatched = plot_df[~plot_df['match']]

    # non-matching points - no hover
    if not unmatched.empty:
        fig.add_trace(go.Scatter(
            x=unmatched['num_users'],
            y=unmatched['average_num_updates'],
            mode='markers',
            marker=dict(
                color=unmatched['time_since_release'],
                colorscale=px.colors.sequential.thermal[::-1],
                size=8,
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
            color=matched['time_since_release'],
            colorscale=px.colors.sequential.thermal[::-1],
            colorbar=dict(title='days since commander release (2 year cap)'),
            size=8,
            opacity=1.0,
        ),
        text=matched['commanders'],
        hovertemplate='<b>%{text}</b><br># users: %{x:,.0f}<br>avg updates: %{y:.3f}<extra></extra>',
        showlegend=False,
    ))

    fig.update_layout(
        title='Breadth (x) vs Depth (y) for commanders in the last two years',
        xaxis=dict(title='# users with a deck for this commander', type='log'),
        yaxis=dict(title='average # deck updates for this commander across users'),
        height=700,
        width=1200,
    )


    return fig

server = app.server

if __name__ == '__main__':
    app.run(debug=True)