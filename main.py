#!/usr/bin/env python
# coding: utf-8

# SCRIPT EM DESENVOLVIMENTO

from matplotlib.backends.backend_agg import RendererAgg
import pandas as pd 
import numpy as np
from datetime import datetime
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
from matplotlib.figure import Figure
import base64
#import pyodbc 

st.set_page_config(layout="wide")


st.title('Data Quality & Assurance')


# # **Leitura do dataset e testes de formatação**


#st.subheader('**Selecione uma das Opções**')
#options = st.radio('O que deseja fazer?',('Carregar Arquivo', 'Conectar ao BD'))
#if options == 'Carregar Arquivo':
#    data = st.file_uploader('Escolha o dataset (.csv)', type = 'csv')
#    if data is not None:
#        df = pd.read_csv(data)
#        df['data'] = pd.to_datetime(df['data'], format='%m/%d/%Y')
#if options == 'Conectar ao BD':
#    import sqlalchemy as db
#    import pandas as pd
#    import pyodbc 
#    from sqlalchemy import create_engine
#    server = st.text_input(label='Server:')
#    database = st.text_input(label='Banco de dados:')
#    username = st.text_input(label='Usuário:')
#    password = st.text_input(label='Senha:')
#    engine = db.create_engine(f"mssql+pyodbc://{username}:{password}@{server}/{database}\
#                        ?driver=ODBC Driver 17 for SQL Server", fast_executemany=True)
#    conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER='+server+';DATABASE='+database+';UID='+username+';PWD='+ password)
#    cursor = conn.cursor()
#    query = "SELECT * FROM Volt_Client_DataScience.bbce.negocios;"
#    df = pd.read_sql(query, conn)
#    conn.close()
#    df['data'] = pd.to_datetime(df['data'], format='%Y-%m-%d')
  

st.header('Testes de Formatação')

df = pd.read_csv('Historico_BBCE.csv', sep=',') 

import io 
matplotlib.use("agg")

_lock = RendererAgg.lock

row3_space1, row3_1, row3_space2, row3_2, row3_space3 = st.columns((.1, 1, .1, 1, .1))

with row3_1, _lock:
    st.write('Formatação Original')
    buffer = io.StringIO()
    df.info(buf=buffer)
    s = buffer.getvalue() 
    with open("df_info.txt", "w", encoding="utf-8") as f:
        st.text(s)



#corrigindo os tipos
df['tend'] = df['tend'].astype('category',copy=False)
df['tipo'] = df['tipo'].astype('category',copy=False)
df['produto'] = df['produto'].astype('category',copy=False)
df['local'] = df['local'].astype('string',copy=False)
df['qtde_mwm'] = df['qtde_mwm'].astype('float',copy=False)
df['qtde_mwh'] = df['qtde_mwh'].astype('float',copy=False)
df['data_completa'] = pd.to_datetime(df['data_completa']) #'%m-%d-%Y %I:%M%p'
df['data'] = pd.to_datetime(df['data'], format='%Y-%m-%d')
df['time'] = pd.to_datetime(df['time'], format='%H:%M:%S')

with row3_2, _lock:
    st.write('Formatação Corrigida')
    buffer = io.StringIO()
    df.info(buf=buffer)
    s = buffer.getvalue() 
    with open("df_info.txt", "w", encoding="utf-8") as f:
        st.text(s)


#colunas para marcar anomalias - Registro com anomalia/outlier = 1
df['avg_preco'] = 0
df['year'] = df['data'].dt.year 
df['flag_datetime'] = 0
df['flag_preco'] = 0

#verificando se há ids duplicados

if len(df['id'].unique()) == len(df.index):
    df.set_index('id', inplace = True)
else:
    st.write('Há '+ str(len(df.index)-len(df['id'].unique())) +' registros duplicados.')

#df.info()


# # **Testes de Consistência**


st.header('Testes de Consistência')

st.subheader('Data e hora')


#checar se há datas inferiores a data de corte inicial ou maiores que a data atual
date_start = datetime.strptime('2017-01-01 00:00:00','%Y-%m-%d %H:%M:%S')
date_now = datetime.now()
st.write('Limites de data esperados -> ' + 'Início: ' + str(date_start) + ' Fim: ' + str(date_now))


date_mask=df[(df['data_completa'] < date_start) | (df['data_completa'] > date_now)]

if  date_mask.shape[0] > 1:

    df['flag_datetime'] = np.where((df['data_completa'] < date_start) | (df['data_completa'] > date_now), 1, 0)

    st.write('Há registros que violam os limites de data:')
    st.write(date_mask)
    
else:
    st.write('Datas dentro dos limites esperados')
#se não retornar itens, não há registros que violem as datas esperadas


# Checar se há operações registradas antes/depois do horário previsto de início/fim das operações.
#Pelas regras de negócio, é esperado operações fora do intervalo 09h-18h para Boleta

st.write('')
time_open = datetime.strptime('08:55:00','%H:%M:%S')
time_close = datetime.strptime('18:30:00','%H:%M:%S')
st.write('Limites de horário esperados -> ' + 'Início: ' + str(time_open) + ' Fim: ' + str(time_close))


#verificação para Balcao
if (df['local'] != 'Boleta' ).any() & (df['time'] < time_open).any():

    df['flag_datetime'] = np.where((df['local'] != 'Boleta' ) & (df['time'] < time_open), 1, 0)
    time_mask_before = df[(df['local'] != 'Boleta' ) & (df['time'] < time_open)]

    count = time_mask_before['time'].count()
    percent = round((time_mask_before['time'].count()/df['produto'].count())*100,2)

    st.write('Há ' + str(count) +
             ' ('+ str(percent)+'%) ' + ' registros que violam os limites de horário inicial:')
    st.write(time_mask_before.groupby(['tipo', 'year']).agg({'flag_datetime':np.sum}))
    st.write(time_mask_before.sort_values(by=['time']))

else:
    st.write('Horários iniciais dentro do limite esperado')


if (df['local'] != 'Boleta' ).any() & (df['time'] > time_close).any():

    df['flag_datetime'] = np.where((df['local'] != 'Boleta' ) & (df['time'] > time_close), 1, 0)

    time_mask_after = df[(df['local'] != 'Boleta' ) & (df['time'] > time_close)]

    count = time_mask_after['time'].count()
    percent = round((time_mask_after['time'].count()/df['produto'].count())*100,2)
    
    st.write('Há ' + str(count) + ' ('+ str(percent) +'%)' +' registros que violam os limites de horário final:')
    st.write(time_mask_after.groupby(['tipo', 'year']).agg({'flag_datetime':np.sum}))
    st.write(time_mask_after.sort_values(by=['time']))

else:
    st.write('Horários finais dentro do limite esperado')


#verificações para Boleta
#time_before = df[(df['local'] == 'Boleta' ) & (df['time'] < time_open)]
#time_before.sort_values(by=['time']).sort_values(by=['time'])

#time_after = df[(df['local'] == 'Boleta' ) & (df['time'] > time_close)]
#time_after.sort_values(by=['time'])

#time_before['time'].count() + time_after['time'].count()



# # **Análises Relacionais**

st.header('Análises Relacionais')

st.subheader('Variações de preço por produto')

#verificar variações abruptas de preço
produto = np.array(df['produto'].unique())
for prod in produto:
    prod_mask = df[(df['produto'] == prod)]
    prod_mask = prod_mask.sort_values(by=['data_completa'])
    data = np.array(prod_mask['data'].unique())
    for date in data:
        data_mask = prod_mask[(prod_mask['data'] == date)]
        #data_mask['preco'] = abs(data_mask['preco'])
        avg = data_mask['preco'].mean()
        df.loc[(df.data == date) & (df.produto == prod), 'avg_preco'] = avg


df['flag_preco'] = np.where((df['preco'] > 1.50*df['avg_preco']) | (abs(df['preco']) < 0.5*df['avg_preco']) , 1, 0)


if (df['flag_preco'] == 1 ).any():
    st.write('Há ' + str(df['flag_preco'].sum()) +' ('+ str(round((df['flag_preco'].sum()/df['flag_preco'].count())*100,2)) +'%)' + ' registros com variações abruptas de preço: ')
    st.write('Variações por ano e por tipo de operação:')
    flag_preco_ano=df[['flag_preco','year','tipo']]
    flag_preco_ano = flag_preco_ano[(flag_preco_ano['flag_preco'] == 1)]
    st.write(flag_preco_ano.groupby(['tipo', 'year']).agg({'flag_preco':np.sum}))
    st.write(df[(df['flag_preco'] == 1)])

else:
    st.write('Variações de preço dentro dos limites esperados.')


st.write('Selecione um produto para visualizar a variação de preço ao longo do tempo.')
sns.set_style('darkgrid')
sec_expander = st.expander(label='Visualizar lista de produtos')
with sec_expander:
    'Escolha os itens que deseja visualizar'
    for prod in produto:
        check = st.checkbox(prod)
        if check:
            prod_mask = df[(df['produto'] == prod)]
            prod_mask = prod_mask.sort_values(by=['data_completa'])
            st.subheader('Variação de preço de ' + prod)
            fig, ax = plt.subplots(figsize=(10,6))
            sns.lineplot(x = prod_mask['data_completa'], y = prod_mask['preco'], markers = True, palette = 'sandybrown', ax=ax)
            ax.set_xlabel("data")
            ax.set_ylabel("preço")
            locs, labels = plt.xticks()
            plt.setp(labels, rotation=45)
            plt.rc('xtick', labelsize=9)
            st.pyplot(fig)



# # **Análise Exploratória dos Dados**
st.header('Data profiling')


# descritivo dos dados
from pandas_profiling import ProfileReport
profile = ProfileReport(df, title=' ', config_file='volt_config.yaml')

#exportar no formato html
#profile.to_file(output_file="dataframe_report.html")

from streamlit_pandas_profiling import st_profile_report

#st.write(df)
st_profile_report(profile)


#disponibilizando arquivo tratado para download
def get_download(df, arq):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode() 
    href = f'<a href="data:file/csv;base64,{b64}" download="'+arq+'.csv">Download</a>'
    return href

st.markdown(get_download(df, 'precos_bbce'), unsafe_allow_html=True)

