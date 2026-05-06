from re import search

from dash import Dash, dcc, html, Input, Output
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

default_style = {
    'font-family': 'Arial, sans-serif'
}

# Load your data into plot_df
plot_df = pd.read_parquet("depth_vs_breadth_plot_df.parquet", engine='pyarrow')

# sort sets by release date
set_order = plot_df.loc[plot_df['parent_set'].apply(len) == 1][['parent_set', 'released_at']].explode('parent_set').drop_duplicates('parent_set').sort_values('released_at')['parent_set'].tolist()

# calculate once outside callback
cmin = plot_df['time_since_release_capped'].min()
cmax = plot_df['time_since_release_capped'].max()

app = Dash(__name__)
app.layout = html.Div([
    html.H2("Breadth (x) vs Depth (y) for commanders in the last two years", style={**default_style}),
    html.Div([
        dcc.Dropdown(
            id='commander-select',
            options=[{'label': c, 'value': c} for c in sorted(plot_df['commanders'].dropna().unique())],
            value=[],
            multi=True,
            placeholder='Select commanders...',
            style={**default_style, 'width': '400px'}
        ),
        dcc.Dropdown(
            id='set-select',
            options=[{'label': s, 'value': s} for s in set_order],
            value=[],
            multi=True,
            placeholder='Select sets...',
            style={**default_style, 'width': '400px'},
            optionHeight=35,  # add this
        ),
        dcc.Dropdown(
            id='color-select',
            options=[{'label': c, 'value': c} for c in sorted(plot_df['color'].dropna().unique())],
            value=[],
            multi=True,
            placeholder='Select colors...',
            style={**default_style, 'width': '400px'}
        ),
    ], style={'display': 'flex', 'gap': '10px', 'margin': '10px'}),
    html.Div(id='no-match-message', style={**default_style, 'color': 'red', 'margin': '10px', 'fontSize': '14px'}),
    dcc.Graph(id='scatter', style={'height': '800px'})
])
@app.callback(
    Output('scatter', 'figure'),
    Output('no-match-message', 'children'),
    Output('commander-select', 'options'),
    Output('set-select', 'options'),
    Output('color-select', 'options'),
    Input('commander-select', 'value'),
    Input('set-select', 'value'),
    Input('color-select', 'value'),
)
def update_figure(selected_commanders, selected_sets, selected_colors):
    any_selection = any([selected_commanders, selected_sets, selected_colors])
    
    if not any_selection:
        matched = plot_df
        unmatched = pd.DataFrame()
        filtered_df = plot_df
    else:
        mask = pd.Series(True, index=plot_df.index)
        
        if selected_commanders:
            mask &= plot_df['commanders'].isin(selected_commanders)
        if selected_colors:
            mask &= plot_df['color'].isin(selected_colors)
        if selected_sets:
            mask &= plot_df['parent_set'].apply(
                lambda x: bool(set(x if x is not None else ()) & set(selected_sets))
            )
        
        matched = plot_df[mask]
        unmatched = plot_df[~mask]
        filtered_df = matched

    # build filtered options from matched set
    # for commanders: show all commanders that match the SET and COLOR filters (but not commander filter)
    set_color_mask = pd.Series(True, index=plot_df.index)
    if selected_sets:
        set_color_mask &= plot_df['parent_set'].apply(
            lambda x: bool(set(x if x is not None else ()) & set(selected_sets))
        )
    if selected_colors:
        set_color_mask &= plot_df['color'].isin(selected_colors)

    commander_options = [{'label': c, 'value': c} for c in sorted(
        set(plot_df[set_color_mask]['commanders'].dropna().unique()) | set(selected_commanders or [])
    )]

    # for sets: show all sets that match the COMMANDER and COLOR filters
    commander_color_mask = pd.Series(True, index=plot_df.index)
    if selected_commanders:
        commander_color_mask &= plot_df['commanders'].isin(selected_commanders)
    if selected_colors:
        commander_color_mask &= plot_df['color'].isin(selected_colors)

    available_sets = set(s for sets in plot_df[commander_color_mask]['parent_set'].dropna() for s in sets)
    set_options = [
        {'label': s, 'value': s} 
        for s in set_order 
        if s in available_sets or s in (selected_sets or [])
    ]

    # for colors: show all colors that match the COMMANDER and SET filters
    commander_set_mask = pd.Series(True, index=plot_df.index)
    if selected_commanders:
        commander_set_mask &= plot_df['commanders'].isin(selected_commanders)
    if selected_sets:
        commander_set_mask &= plot_df['parent_set'].apply(
            lambda x: bool(set(x if x is not None else ()) & set(selected_sets))
        )

    color_options = [{'label': c, 'value': c} for c in sorted(
        set(plot_df[commander_set_mask]['color'].dropna().unique()) | set(selected_colors or [])
    )]
    if any_selection and matched.empty:
        message = "No commanders match the selected combination."
    else:
        message = ""

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
                color=unmatched['time_since_release_capped'],
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
            color=matched['time_since_release_capped'],
            colorbar=dict(title='days since commander release (2 year cap)'),
            opacity=0.8,
        ),
        text=matched['commanders'],
        customdata=matched[['time_since_release', 'color', 'parent_set']].values,
        hovertemplate=(
            '<b>%{text}</b><br>'
            'color: %{customdata[1]}<br>'
            'sets: %{customdata[2]}<br>'
            'days since release: %{customdata[0]:.0f}<br>'
            '# users: %{x:,.0f}<br>'
            'avg updates: %{y:.3f}<br>'
            '<extra></extra>'
        ),
        showlegend=False,
    ))

    fig.update_layout(
        title='Depth vs breadth of commanders',
        xaxis=dict(title='Breadth = # users with a deck for this commander (log scale)', type='log'),
        yaxis=dict(title='Depth = average deck updates for this commander across users'),
    )

    return fig, message, commander_options, set_options, color_options

server = app.server

if __name__ == '__main__':
    app.run(debug=True)