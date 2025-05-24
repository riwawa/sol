import os # manipulação de arquivos e diretórios (ex. cache)
import requests # requisições HTTP à API
import numpy as np # dados
import pandas as pd # dados
import matplotlib.pyplot as plt # plotagem de gráfico e mapas
import cartopy.crs as ccrs # plotagem de mapa e gráficos
import cartopy.feature as cfeature # plotagem de mapa e gráficos
from matplotlib import cm 
from scipy.interpolate import griddata # interpolação de dados espaciais
import concurrent.futures # parelização de requisições - serve pra deixar mais rapido o carregamento
import time


def obter_coordenadas(cidade):
    """Usa o API pra obter a longitude e latitude de 1 cidade"""
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={requests.utils.quote(cidade)}&count=1"
    res = requests.get(url)
    res.raise_for_status()
    dados = res.json()
    if not dados.get('results'):
        raise ValueError("Nenhuma coordenada encontrada para a cidade.")
    return dados['results'][0]['latitude'], dados['results'][0]['longitude']

def buscar_dados_clima(cidade, ano):
    """busca e transforma em cache os dados da cidade"""
    pasta = os.path.join("dados", cidade.replace(" ", "_"), str(ano)) # define a pasta para armazenar os dados, nesse caso a pasta dados
    os.makedirs(pasta, exist_ok=True)
    arquivo = os.path.join(pasta, f"dados_{cidade.replace(' ', '_')}_{ano}.csv")

    if os.path.exists(arquivo): # se o arquivo já existe, carrega os dados com pandas e retorna
        df = pd.read_csv(arquivo, parse_dates=['date'])
        return df
        
    # se nao, chamada o obter coordenadas para pegar lat/lon da cidade
    lat, lon = obter_coordenadas(cidade)
    url = (
        "https://archive-api.open-meteo.com/v1/archive?"
        f"latitude={lat}&longitude={lon}&start_date={ano}-01-01&end_date={ano}-12-31"
        "&daily=temperature_2m_max,temperature_2m_min"
        "&timezone=America%2FSao_Paulo"
    )

    res = requests.get(url) # faz requisicao
    res.raise_for_status()
    dados = res.json() # valida a resposta
    if not dados.get('daily'): # se nao encontrar dados, mensagem de erro
        raise ValueError("Dados climáticos não encontrados para o ano.")

    df = pd.DataFrame({
        'lon': [lon] * len(dados['daily'].get('time', [])),
        "date": pd.to_datetime(dados['daily'].get('time', [])),
        "temp_max": dados['daily'].get('temperature_2m_max', [None] * len(dados['daily'].get('time', []))),
        "temp_min": dados['daily'].get('temperature_2m_min', [None] * len(dados['daily'].get('time', []))),
    })

    lat, lon = obter_coordenadas(cidade)  # garante que tem lat/lon mesmo carregando do CSV
 
    df["temp"] = df[['temp_max', 'temp_min']].mean(axis=1) # cria coluna temp que é a média das temperaturas máxima e mínima
    df.to_csv(arquivo, index=False) # salva o dataframe em CSV para cache
    return df # retorna o dataframe

def grafico_temperatura(df, cidade, ano):
    """Gera gráfico de temperatura média mensal usando os dados já adquiridos na função anterior"""
    df['mes'] = df['date'].dt.month # cria a coluna mes extraída da coluna de datas
    medias = df.groupby('mes')['temp'].mean().reindex(range(1, 13)) # agrupa os dados por mês

    # PROJECAO GRÁFICA -----
    fig, ax = plt.subplots(figsize=(6, 6)) # tamanho do gráfico de barra
    colors = cm.coolwarm((medias - medias.min()) / (medias.max() - medias.min()))
    ax.bar(medias.index, medias.values, color=colors) # define cores para as barras baseada na temperatura relativa pelo colormap coolwarm
    ax.set_xticks(medias.index)  
    ax.set_xticklabels(['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']) # no eixo x, vai ter os nomes dos meses (ticks)
    ax.set_xlabel("Mês") # no eixo x, vai ter o nome mes
    ax.set_ylabel("Temperatura Média (°C)") 
    ax.set_title(f"Temperatura média mensal em {cidade} ({ano})")
    ax.grid(axis='y')

    return fig

def buscar_dados_ponto(lat, lon, ano, tentativas=3, delay=5):
    pasta_cache = os.path.join("dados", "cache_pontos", f"{lat}_{lon}", str(ano))
    os.makedirs(pasta_cache, exist_ok=True)
    arquivo_cache = os.path.join(pasta_cache, "dados.csv")

    if os.path.exists(arquivo_cache):
        df = pd.read_csv(arquivo_cache)
        temp_media = df["temp"].mean()  
        return ( (lat, lon), {"temp": temp_media} )

    url = (
        "https://archive-api.open-meteo.com/v1/archive?"
        f"latitude={lat}&longitude={lon}&start_date={ano}-01-01&end_date={ano}-12-31"
        "&daily=temperature_2m_max,temperature_2m_min"
        "&timezone=America%2FSao_Paulo"
    )
    
    for tentativa in range(tentativas):
        try:
            res = requests.get(url)
            res.raise_for_status()
            dados = res.json()
            if not dados.get('daily'):
                raise ValueError("Dados climáticos não encontrados para o ponto.")
            df = pd.DataFrame({
                "date": pd.to_datetime(dados['daily'].get('time', [])),
                "temp_max": dados['daily'].get('temperature_2m_max', []),
                "temp_min": dados['daily'].get('temperature_2m_min', []),
            })
            df["temp"] = df[['temp_max', 'temp_min']].mean(axis=1)
            df.to_csv(arquivo_cache, index=False)
            temp_media = df["temp"].mean()
            return ( (lat, lon), {"temp": temp_media} )
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                print(f"Erro 429 - esperando {delay}s para tentar novamente... (tentativa {tentativa+1}/{tentativas})")
                time.sleep(delay)
            else:
                print(f"Erro HTTP: {e}")
                return None
        except Exception as e:
            print(f"Erro ao buscar dados no ponto ({lat}, {lon}): {e}")
            return None
    return None


def gerar_mapa_temperatura(cidade, ano):   
    pasta_base = os.path.join("dados", cidade.replace(" ", "_"), str(ano))
    pasta_cache = os.path.join(pasta_base, "cache_mapas")
    os.makedirs(pasta_cache, exist_ok=True)

    nome_arquivo = os.path.join(pasta_cache, f"{cidade.replace(' ', '_')}_{ano}.png")

    if os.path.exists(nome_arquivo): # caso o mapa está no cache, ele retorna a figura do cache
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.imshow(plt.imread(nome_arquivo))
        ax.axis('off')
        return fig

    # caso contrário:
    print("Gerando novo mapa...")

    lat_c, lon_c = obter_coordenadas(cidade) # obtém a latitude e longitude da cidade
    tamanho_grid = 15 # define uma grade tamanho 15x15
    lat_range = np.linspace(lat_c - 5, lat_c + 5, tamanho_grid) # cobre uma area de 10 graus
    lon_range = np.linspace(lon_c - 5, lon_c + 5, tamanho_grid) # cobre uma area de 10 graus

    pontos = []
    temperaturas = []
 

    # criar lista de todos os pontos (lat, lon)
    lista_pontos = [(lat, lon) for lat in lat_range for lon in lon_range]

    # paralelizar requisições
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        resultados = executor.map(lambda p: buscar_dados_ponto(p[0], p[1], ano), lista_pontos)
    for resultado in resultados:
        if resultado is not None:
            ponto, dados = resultado
            if dados and 'temp' in dados and dados['temp'] is not None:
                pontos.append(ponto)
                temperaturas.append(dados['temp'])

    # interpolação dos dados
    lon_grid, lat_grid = np.meshgrid(
        np.linspace(lon_c - 5, lon_c + 5, 100),
        np.linspace(lat_c - 5, lat_c + 5, 100)
    )
    temp_grid = griddata(pontos, temperaturas, (lon_grid, lat_grid), method='linear')
 
    # PROJEÇÃO DO MAPA -------
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={'projection': ccrs.PlateCarree()})
    ax.set_extent([lon_c - 5, lon_c + 5, lat_c - 5, lat_c + 5])
    ax.add_feature(cfeature.COASTLINE)
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    cont = ax.contourf(lon_grid, lat_grid, temp_grid, cmap='coolwarm', transform=ccrs.PlateCarree())
    plt.colorbar(cont, ax=ax, label='Temperatura Média Anual (°C)')
    ax.set_title(f"Mapa de Temperatura em {cidade} ({ano})")

    fig.savefig(nome_arquivo)
    return fig
