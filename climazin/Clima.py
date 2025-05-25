from shiny import App, ui, render, reactive
import pandas as pd
import numpy as np
from cidades import cidades
from ClimaAPI import buscar_dados_clima, obter_coordenadas, grafico_temperatura, gerar_mapa_temperatura, grafico_chuva
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.cm as cm
import matplotlib.colors as mcolors


print("Carregando dados...")

anos = list(range(2000, 2025))

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_select("tipo_dado", "Tipo de dado:", choices=["Temperatura", "Precipitação", "Vento"]),
        ui.input_select("tipo_vis", "Tipo de visualização:", choices=["Gráfico", "Mapa"]),

        # ui.input_select("modo", "Modo de visualização:", choices=["Gráfico", "Mapa", "Chuva"], selected="Gráfico"),
        ui.input_select('cidade', 'Escolha a cidade:', choices=cidades),
        ui.input_slider('ano', 'Escolha o ano:', min=min(anos), max=max(anos), value=min(anos), step=1),
        style='background-color: white; height: 100vh;'
    ),
    ui.column(
        12,
        ui.h2('Visualizador Climático'),
        ui.div(
            ui.panel_conditional("input.tipo_dado == 'Temperatura' && input.tipo_vis == 'Gráfico'", ui.output_plot('graficoTemp')),
            ui.panel_conditional("input.tipo_dado == 'Temperatura' && input.tipo_vis == 'Mapa'", ui.output_plot('mapaTemp')),
            ui.panel_conditional("input.tipo_dado == 'Precipitação' && input.tipo_vis == 'Gráfico'", ui.output_plot('graficoChuva')),
            ui.panel_conditional("input.tipo_dado == 'Precipitação' && input.tipo_vis == 'Mapa'", ui.output_ui("avisoMapa")),
            ui.panel_conditional("input.tipo_dado == 'Vento' && input.tipo_vis == 'Mapa'", ui.output_plot('ventoMapa')),
            ui.panel_conditional("input.tipo_dado == 'Vento' && input.tipo_vis == 'Gráfico'", ui.output_ui("avisoGrafico")),

            style='background: linear-gradient(to bottom, #87cefa, white); padding: 20px; border-radius: 10px; width: 100%; box-shadow: 0 4px 20px rgba(0, 0, 0 , 0.3);'           
        ),    
        ui.tags.style("""
            body {
            background: linear-gradient(to bottom, #a6a6a6, white);
            min-height: 100vh;
            margin: 0;
        }
     """),
        
        
    ),


)

def server(input, output, session):

    @output
    @render.ui
    def avisoMapa():
        return ui.div({
            "style": "padding: 20px; background-color: #ffdddd; color: #a33; border-radius: 10px; border: 1px solid #a33;"
        }, "Mapa desse modo não está disponível.")

    def avisoGrafico():
        return ui.div({
            "style": "padding: 20px; background-color: #ffdddd; color: #a33; border-radius: 10px; border: 1px solid #a33;"
        }, "Gráfico desse modo não está disponível.")

    @reactive.Calc
    def dados_filtrados():
        return buscar_dados_clima(input.cidade(), input.ano())

    @output
    @render.plot
    def graficoTemp():
        df = dados_filtrados()
        return grafico_temperatura(df, input.cidade(), input.ano())
        
    @output
    @render.plot
    def mapaTop():
        cidade = input.cidade()
        ano = input.ano()
        fig = gerar_mapa_temperatura(cidade, ano)
        return fig

    @output
    @render.plot
    def graficoChuva():
        df = dados_filtrados()
        return grafico_chuva(df, input.cidade(), input.ano())

    @output
    @render.plot
    def ventoMapa():
        
app = App(app_ui, server)

if __name__ == "__main__":
    import shiny
    print("Iniciando o app em http://127.0.0.1:8000")
    shiny.run_app(app, port=8000, host="0.0.0.0")
