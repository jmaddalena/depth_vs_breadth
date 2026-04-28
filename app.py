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

    fig.add_trace(go.Scatter(
        x=plot_df['num_users'],
        y=plot_df['average_num_updates'],
        mode='markers',
        marker=dict(
            color=plot_df['time_since_release'],
            colorscale=px.colors.sequential.thermal[::-1],
            colorbar=dict(title='days since commander release (2 year cap)'),
            size=8,
            opacity=plot_df['match'].map({True: 1.0, False: 0.1}).tolist(),
        ),
        text=plot_df['commanders'],
        hovertemplate='<b>%{text}</b><br># users: %{x:,.0f}<br>avg updates: %{y:.3f}<extra></extra>',
    ))

    fig.update_layout(
        title='Breadth (x) vs Depth (y) for commanders in the last two years',
        xaxis=dict(title='# users with a deck for this commander', type='log'),
        yaxis=dict(title='average # deck updates for this commander across users'),
        height=1000,
        width=2000,
    )

    return fig

if __name__ == '__main__':
    app.run(debug=True)