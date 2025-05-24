<div align="center">
  <h1>Sol</h1>
  <p><strong>Projeto acadêmico desenvolvido em ambiente EC2 (AWS)</strong></p>
</div>

<p align="center">
  <img src="https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54" alt="Python" />
  <img src="https://img.shields.io/badge/shiny-1f425f?style=for-the-badge&logo=shiny&logoColor=white" alt="Shiny" />
  <img src="https://img.shields.io/badge/aws-232F3E?style=for-the-badge&logo=amazon-aws&logoColor=white" alt="AWS" />
  <img src="https://img.shields.io/badge/status-desenvolvimento-yellow?style=for-the-badge" alt="Em desenvolvimento" />
</p>

---


**Sol** é uma aplicação desenvolvida com o objetivo de coletar, processar e analisar dados climáticos provenientes da API [OpenMeteo](https://open-meteo.com/).

Este sistema foi criado como parte de um **projeto acadêmico da disciplina de Introdução à Programação**, no primeiro semestre do curso de Engenharia de Computação.

A aplicação realiza a conexão com a API OpenMeteo, processa as informações meteorológicas e exibe a temperatura, umidade, chuva, vento e pressão atmosférica.

Todo o desenvolvimento e execução do sistema foram feitos dentro de uma instância **EC2 da AWS**, simulando um ambiente real de implantação em nuvem.


## Tecnologias Utilizadas

- Python
- Shiny Framework
- API OpenMeteo
- AWS EC2

## Instalação

Etapas para instalar Sol

1. Clone esse repositório
```bash
  git clone [link]
  cd climazin
```
2. Para instalar todas as dependências e bibliotecas necessários para o programa funcionar, no terminal, rode:
```bash
./activate_and_install.sh
```
Se o script não estiver com permissão de execução, execute antes:

```bash
chmod +x activate_and_install.sh
./activate_and_install.sh
```

Após isso, o ambiente estará pronto para rodar o projeto.

Para iniciar o programa, execute:
```bash
python Clima.py
```

## Equipe

- [Beatriz Lucena](https://www.github.com/riwawa)
- [Filipe](https://github.com/lipeollv)
- [Ian Hoda](https://github.com/Jank52)

