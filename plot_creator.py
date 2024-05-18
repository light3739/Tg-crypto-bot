import logging
import plotly.graph_objects as go
import os

from config import IMAGES_DIR

logger = logging.getLogger(__name__)


def create_plot(df, crypto):
    if df.empty:
        logger.error("DataFrame пуст. Невозможно создать график.")
        return
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(x=df['timestamp'], y=df['price'], mode='lines', name='Цена', line=dict(color='royalblue', width=2)))

    fig.add_trace(
        go.Scatter(x=df['timestamp'], y=df['SMA'], mode='lines', name='SMA', line=dict(color='orange', width=2)))

    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['Upper Band'], mode='lines', name='Верхняя полоса',
                             line=dict(color='lightgrey', width=1)))
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['Lower Band'], mode='lines', name='Нижняя полоса',
                             line=dict(color='lightgrey', width=1), fill='tonexty',
                             fillcolor='rgba(173, 216, 230, 0.2)'))

    fig.update_layout(
        title={
            'text': f'Цена {crypto.capitalize()} за последние 90 дней',
            'y': 0.9,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        xaxis_title='Дата',
        yaxis_title='Цена (USD)',
        template='plotly_white'
    )

    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')

    fig.update_traces(hoverinfo='x+y', mode='lines+markers', marker=dict(size=5))

    max_price = df['price'].max()
    min_price = df['price'].min()
    max_date = df[df['price'] == max_price]['timestamp'].iloc[0]
    min_date = df[df['price'] == min_price]['timestamp'].iloc[0]

    fig.add_annotation(
        x=max_date, y=max_price,
        text=f'Макс: {max_price:.2f}',
        showarrow=True,
        arrowhead=1,
        ax=0, ay=-40,
        bgcolor="white",
        bordercolor="black",
        borderwidth=1
    )
    fig.add_annotation(
        x=min_date, y=min_price,
        text=f'Мин: {min_price:.2f}',
        showarrow=True,
        arrowhead=1,
        ax=0, ay=40,
        bgcolor="white",
        bordercolor="black",
        borderwidth=1
    )

    file_path = os.path.join(IMAGES_DIR, f'{crypto}.png')
    try:
        fig.write_image(file_path)
        logger.info(f"График создан и сохранен в {file_path}")
    except Exception as e:
        logger.error(f"Ошибка при сохранении графика в {file_path}: {e}")


def create_indicators_plot(df, crypto):
    if df.empty:
        logger.error("DataFrame пуст. Невозможно создать график индикаторов.")
        return
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(x=df['timestamp'], y=df['MACD'], mode='lines', name='MACD', line=dict(color='green', width=2)))
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['Signal Line'], mode='lines', name='Сигнальная линия',
                             line=dict(color='red', width=2)))

    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['%K'], mode='lines', name='%K', line=dict(color='blue', width=2)))
    fig.add_trace(
        go.Scatter(x=df['timestamp'], y=df['%D'], mode='lines', name='%D', line=dict(color='purple', width=2)))

    fig.update_layout(
        title={
            'text': f'Индикаторы {crypto.capitalize()} за последние 30 дней',
            'y': 0.9,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        xaxis_title='Дата',
        yaxis_title='Значение',
        template='plotly_white'
    )

    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')

    fig.update_traces(hoverinfo='x+y', mode='lines+markers', marker=dict(size=5))

    file_path = os.path.join(IMAGES_DIR, f'{crypto}_indicators.png')
    try:
        fig.write_image(file_path)
        logger.info(f"График индикаторов создан и сохранен в {file_path}")
    except Exception as e:
        logger.error(f"Ошибка при сохранении графика индикаторов в {file_path}: {e}")


def create_gauge(value, title, max_value):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={'text': title},
        gauge={
            'axis': {'range': [None, max_value]},
            'bar': {'color': "darkblue"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, max_value * 0.5], 'color': 'lightgray'},
                {'range': [max_value * 0.5, max_value], 'color': 'gray'}],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': value}}))
    return fig
