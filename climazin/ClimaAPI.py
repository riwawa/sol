import os # manipulação de arquivos e diretórios (ex. cache)
import requests # requisições HTTP à API
import numpy as np # dados
import pandas as pd # dados
import matplotlib.pyplot as plt # plotagem de gráfico e mapas
import cartopy.crs as ccrs # plotagem de mapa e gráficos
import cartopy.feature as cfeature # plotagem de mapa e gráficos
from matplotlib import cm 
from metpy.interpolate import interpolate_to_grid
from metpy.units import units
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
    pasta = os.path.join("dados", cidade.replace(" ", "_"), str(ano))
    os.makedirs(pasta, exist_ok=True)
    arquivo = os.path.join(pasta, f"dados_{cidade.replace(' ', '_')}_{ano}.csv")

    if os.path.exists(arquivo): 
        df = pd.read_csv(arquivo, parse_dates=['date'])
        
        # Verifica se a coluna 'precipitacao' está no DataFrame
        if 'precipitacao' not in df.columns:
            print("Cache antigo sem coluna 'precipitacao'. Atualizando cache...")
        else:
            return df  # coluna existe, retorna o df normalmente

    # Se não existe o arquivo ou cache antigo está incompleto, baixa da API
    lat, lon = obter_coordenadas(cidade)
    url = (
        "https://archive-api.open-meteo.com/v1/archive?"
        f"latitude={lat}&longitude={lon}&start_date={ano}-01-01&end_date={ano}-12-31"
        "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
        "&timezone=America%2FSao_Paulo"
    )

    res = requests.get(url)
    res.raise_for_status()
    dados = res.json()
    if not dados.get('daily'):
        raise ValueError("Dados climáticos não encontrados para o ano.")

    df = pd.DataFrame({
        'lon': [lon] * len(dados['daily'].get('time', [])),
        "date": pd.to_datetime(dados['daily'].get('time', [])),
        "temp_max": dados['daily'].get('temperature_2m_max', [None] * len(dados['daily'].get('time', []))),
        "temp_min": dados['daily'].get('temperature_2m_min', [None] * len(dados['daily'].get('time', []))),
        "precipitacao": dados['daily'].get('precipitation_sum', [None] * len(dados['daily'].get('time', []))),
    })

    df["temp"] = df[['temp_max', 'temp_min']].mean(axis=1)
    df.to_csv(arquivo, index=False)
    return df

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

    fig.savefig(nome_arquivo,)

    plt.tight_layout(pad=0)
    return fig

def grafico_chuva(df, cidade, ano):
    """gera gráfico de precipitacao media mensal"""
    df = buscar_dados_clima(cidade, ano)  
    
    if 'precipitacao' not in df.columns:
        raise ValueError("A coluna 'precipitacao' não está presente no DataFrame retornado.")
    
    data_set = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    df['mes'] = df['date'].dt.month
    soma_mensal = df.groupby('mes')['precipitacao'].sum().reindex(range(1, 13))

    # criar a figura
    fig, ax = plt.subplots(figsize=(6,6))
    # desenhar o grafico
    bars = ax.bar(soma_mensal.index, soma_mensal.values, color='skyblue', width = 0.5)

    # eixo x
    ax.set_xticks(soma_mensal.index)
    ax.set_xticklabels(data_set)
    ax.set_xlabel("Mês") #nome do eixo x

    # eixo precipitacao
    ax.grid(False)
    ax.set_ylabel("Precipitação Total (mm)") # nome do eixo y (esquerdo)
    ax.set_ylim(0,450)
    ax.set_title(f"Precipitação mensal de {cidade} em {ano}")

    return fig

def calcular_vetor(df_vento):
    ang_rad = np.deg2rad(df_vento['direcao'])
    df_vento['u'] = -df_vento['velocidade'] * np.sin(ang_rad)
    df_vento['v'] = -df_vento['velocidade'] * np.cos(ang_rad)
    return df_vento

def gerar_grade(lat_centro, lon_centro, delta=0.2, n=5):
    lats = np.linspace(lat_centro - delta, lat_centro + delta, n)
    lons = np.linspace(lon_centro - delta, lon_centro + delta, n)
    return [(lat, lon) for lat in lats for lon in lons]

def agrupar_por_direcao(df):
    df['setor'] = (df['direcao'] // 60 * 60).astype(int)
    df_media_setor = df.groupby('setor').agg({
        'u': 'mean',
        'v': 'mean',
        'lat': 'first',
        'lon': 'first',
        'velocidade': 'count'
    }).reset_index()
    df_media_setor = df_media_setor[df_media_setor['velocidade'] > 300]
    return df_media_setor[['u', 'v', 'lat', 'lon']] if not df_media_setor.empty else pd.DataFrame(columns=['u', 'v', 'lat', 'lon'])

def buscar_dados_vento_ponto(lat, lon, ano, cidade):
    pasta = os.path.join("dados", cidade.replace(" ", "_"), str(ano))
    os.makedirs(pasta, exist_ok=True)
    arquivo = os.path.join(pasta, f"vento_{lat:.2f}_{lon:.2f}.csv")

    if os.path.exists(arquivo):
        df_vento = pd.read_csv(arquivo, parse_dates=['hora'])
        if all(col in df_vento.columns for col in ['velocidade', 'direcao', 'u', 'v']):
            return agrupar_por_direcao(df_vento)

    url = (
        f"https://archive-api.open-meteo.com/v1/archive?"
        f"latitude={lat}&longitude={lon}&start_date={ano}-01-01&end_date={ano}-12-31"
        "&hourly=wind_speed_10m,wind_direction_10m&timezone=America%2FSao_Paulo"
    )
    res = requests.get(url)
    res.raise_for_status()
    dados = res.json()

    if not dados.get('hourly') or not dados['hourly'].get('time'):
        return None

    df_vento = pd.DataFrame({
        "hora": pd.to_datetime(dados['hourly']['time']),
        "velocidade": dados['hourly']['wind_speed_10m'],
        "direcao": dados['hourly']['wind_direction_10m'],
        "lat": lat,
        "lon": lon
    })

    df_vento = calcular_vetor(df_vento)
    df_vento.to_csv(arquivo, index=False)
    return agrupar_por_direcao(df_vento)

def coletar_grade_vento(cidade, ano):
    lat_centro, lon_centro = obter_coordenadas(cidade)
    pontos = gerar_grade(lat_centro, lon_centro, delta=1, n=5)
    df_lista = []

    for lat, lon in pontos:
        try:
            df_ponto = buscar_dados_vento_ponto(lat, lon, ano, cidade)
            if df_ponto is not None:
                df_lista.append(df_ponto)
        except Exception as e:
            print(f"Erro no ponto {lat},{lon}: {e}")
    return pd.concat(df_lista, ignore_index=True) if df_lista else pd.DataFrame(columns=['u', 'v', 'lat', 'lon'])

def plotar_isobaras(ax, df_grade):
    if 'pressao' not in df_grade.columns:
        df_grade['pressao'] = 1013 - (df_grade['v'] + df_grade['u']) * 2

    xi, yi, zi = interpolate_to_grid(df_grade['lon'], df_grade['lat'], df_grade['pressao'], hres=0.1)

    cs = ax.contour(xi, yi, zi, levels=range(990, 1030, 4), colors='black', linewidths=1, transform=ccrs.PlateCarree())
    ax.clabel(cs, inline=True, fontsize=8, fmt='%d hPa')

def marcar_centros_pressao(ax, df_grade):
    if 'pressao' not in df_grade.columns:
        return
    max_ponto = df_grade.loc[df_grade['pressao'].idxmax()]
    min_ponto = df_grade.loc[df_grade['pressao'].idxmin()]
    for ponto, label, cor in [(max_ponto, 'H', 'blue'), (min_ponto, 'L', 'red')]:
        ax.text(ponto['lon'], ponto['lat'], label, fontsize=20, weight='bold', color=cor,
                ha='center', va='center', transform=ccrs.PlateCarree())
def mapa_vento(cidade, ano):
    df_grade = coletar_grade_vento(cidade, ano)
    lat_centro, lon_centro = obter_coordenadas(cidade)

    df_grade['u'] = pd.to_numeric(df_grade['u'], errors='coerce')
    df_grade['v'] = pd.to_numeric(df_grade['v'], errors='coerce')
    df_grade = df_grade.dropna(subset=['u', 'v'])

    # Interpolação para grade 2D
    lon_vals = df_grade['lon'].values
    lat_vals = df_grade['lat'].values
    u_vals = df_grade['u'].values
    v_vals = df_grade['v'].values

    lon_grid, lat_grid = np.meshgrid(
        np.linspace(lon_vals.min(), lon_vals.max(), 100),
        np.linspace(lat_vals.min(), lat_vals.max(), 100)
    )

    u_grid = griddata((lon_vals, lat_vals), u_vals, (lon_grid, lat_grid), method='linear')
    v_grid = griddata((lon_vals, lat_vals), v_vals, (lon_grid, lat_grid), method='linear')
    intensidade_grid = np.sqrt(u_grid**2 + v_grid**2)

    proj = ccrs.Mercator()
    fig, ax = plt.subplots(figsize=(12, 8), subplot_kw={'projection': proj})
    ax.set_extent([lon_centro - 2, lon_centro + 2, lat_centro - 2, lat_centro + 2], crs=ccrs.PlateCarree())

    ax.add_feature(cfeature.LAND.with_scale('50m'), facecolor='lightgray')
    ax.add_feature(cfeature.OCEAN.with_scale('50m'))
    ax.add_feature(cfeature.COASTLINE.with_scale('50m'))
    ax.add_feature(cfeature.BORDERS.with_scale('50m'), linestyle=':')
    ax.add_feature(cfeature.LAKES.with_scale('50m'), alpha=0.5)
    ax.add_feature(cfeature.RIVERS.with_scale('50m'))

    # Pontilhado com intensidade
    sc = ax.scatter(
        df_grade['lon'], df_grade['lat'],
        c=np.sqrt(df_grade['u']**2 + df_grade['v']**2),
        cmap='plasma', s=30, alpha=0.8,
        transform=ccrs.PlateCarree()
    )
    plt.colorbar(sc, ax=ax, orientation='vertical', label='Velocidade do vento (m/s)')

    # Linhas de corrente (streamplot)
    ax.streamplot(
        lon_grid, lat_grid, u_grid, v_grid,
        color=intensidade_grid,
        cmap='plasma',
        linewidth=1.5,
        density=2,
        transform=ccrs.PlateCarree()
    )

    plotar_isobaras(ax, df_grade)
    marcar_centros_pressao(ax, df_grade)

    # Rosa dos ventos
    lon_leg, lat_leg = lon_centro + 1.5, lat_centro - 1.5
    legenda = pd.DataFrame({'direcao': [0, 90, 180, 270], 'label': ['N', 'E', 'S', 'O']})
    ang_rad = np.deg2rad(legenda['direcao'])
    legenda['u'] = -np.sin(ang_rad)
    legenda['v'] = -np.cos(ang_rad)
    legenda['lat'] = lat_leg
    legenda['lon'] = lon_leg

    ax.quiver(
        legenda['lon'], legenda['lat'],
        legenda['u'], legenda['v'],
        transform=ccrs.PlateCarree(),
        color='black', scale=10, width=0.005
    )

    offset = 0.15
    for _, row in legenda.iterrows():
        ax.text(row['lon'] + row['u'] * offset, row['lat'] + row['v'] * offset,
                row['label'], transform=ccrs.PlateCarree(),
                ha='center', va='center', fontsize=10, weight='bold')

    ax.set_title(f'Mapa de vento médio anual em {cidade} em {ano}')
    return fig
