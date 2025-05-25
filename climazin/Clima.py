from shiny import App, ui, render, reactive
import pandas as pd
import numpy as np
from cidades import cidades
from ClimaAPI import buscar_dados_clima, obter_coordenadas, grafico_temperatura, gerar_mapa_temperatura
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.cm as cm
import matplotlib.colors as mcolors


print("Carregando dados...")

anos = list(range(2000, 2025))

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_select("modo", "Modo de visualização:", choices=["Gráfico", "Mapa"], selected="Gráfico"),
        ui.input_select('cidade', 'Escolha a cidade:', choices=cidades),
        ui.input_slider('ano', 'Escolha o ano:', min=min(anos), max=max(anos), value=min(anos), step=1),
        style='background-color: white; height: 100vh;'
    ),
    ui.column(
        12,
        ui.div( # Titulo
            ui.h2('Visualizador Climático', style='background-color: #004578; color: white; font-family: "Arial Black"; padding: 10px 20px; border-radius: 10px;'),
        ),
        ui.div( # Gráfico
            ui.panel_conditional("input.modo == 'Gráfico'", ui.output_plot('graficoTemp')),
            ui.panel_conditional("input.modo == 'Mapa'", ui.output_plot('mapaTop', width='900px', height='900px')),
            style='background: linear-gradient(to bottom, #004578, #7ba8c9); padding: 10px; border-radius: 10px; width: 100%; box-shadow: 0 4px 20px rgba(0, 0, 0 , 0.3); margin-top: 50px;',          
        ),    
        ui.tags.style(""" 
            body {
            background: linear-gradient(to bottom, #87cefa, white); 
            min-height: 100vh;
            margin: 0;
        }
     """), # Plano de fundo (cor) 
        
        
    ),


)

def server(input, output, session):

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


app = App(app_ui, server)

if __name__ == "__main__":
    import shiny
    print("Iniciando o app em http://127.0.0.1:8000")
    shiny.run_app(app, port=8000, host="0.0.0.0")
