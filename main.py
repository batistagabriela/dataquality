#!/usr/bin/env python
# coding: utf-8

# SCRIPT EM DESENVOLVIMENTO

# In[1]:


from matplotlib.backends.backend_agg import RendererAgg
import pandas as pd 
import numpy as np
from scipy import stats
from datetime import datetime, timedelta, date, time
from dateutil.relativedelta import relativedelta
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
from matplotlib.figure import Figure
import base64
#import pyodbc 

st.set_page_config(layout="wide")


# In[2]:


st.title('Relatório de Qualidade dos Dados:')
st.title('Validação, Análise e Tratamento')


# In[3]:


#lendo o dataset


df = pd.read_csv('BBCE.csv', sep=',')
df.drop('Unnamed: 0', axis=1, inplace=True)
df.drop('flag_validacao', axis=1, inplace=True)
df.drop('flag_user', axis=1, inplace=True)
tags = df.columns


# # **Testes de Integridade**

# In[5]:


st.header('Testes de Integridade')

#verificando se há ids duplicados
if len(df['id'].unique()) == len(df.index):
    st.write('Não há registros duplicados.')
    check_duplicados = 'Não'
    qtd_duplicados = 0
else:
    check_duplicados = 'Sim'
    qtd_duplicados = (len(df.index)-len(df['id'].unique()))
    st.write(f'Há {qtd_duplicados} registros duplicados.')

#verificando se há valores nulos 
if df.isnull().sum().any():
    check_null = 'Sim'
    qtd_null = df.isnull().sum().sum()
    st.write(f'Há {qtd_null} registros nulos.')
else:
    check_null = 'Não'
    qtd_null = 0
    st.write('Não há registros nulos.')

st.subheader('Validação da formatação')

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

#corrigindo os tipos pra facilitar a vida
df['tend'] = df['tend'].astype('category',copy=False)
df['tipo'] = df['tipo'].astype('category',copy=False)
df['produto'] = df['produto'].astype('string',copy=False)
df['local'] = df['local'].astype('string',copy=False)
df['qtde_mwm'] = df['qtde_mwm'].astype('float',copy=False)
df['qtde_mwh'] = df['qtde_mwh'].astype('float',copy=False)
df['data_completa'] = pd.to_datetime(df['data_completa']) 
df['data'] = df['data_completa'].apply(lambda x: datetime.date(x))
df['time'] = df['data_completa'].apply(lambda x: datetime.time(x))


with row3_2, _lock:
    st.write('Formatação Corrigida')
    buffer = io.StringIO()
    df.info(buf=buffer)
    s = buffer.getvalue() 
    with open("df_info.txt", "w", encoding="utf-8") as f:
        st.text(s)


#correções de texto, inclusão de colunas para suporte

#colunas com abertura de data da operação - para usar no calculo de maturidade
df['ano_op'] = df['data_completa'].dt.year 
df['mes_ano_op'] = pd.to_datetime(df['ano_op'].astype(str) + df['data_completa'].dt.month.astype(str) , format='%Y%m')
df['mes_ano_op'] = df['mes_ano_op'].apply(lambda x: datetime.date(x))

#eliminando diferenças de upper/lower
df['produto'] = df['produto'].str.upper()


import re

#identificar a data inicial no produto
def data_produto(txt):
    month = ['FEB', 'APR', 'MAY', 'AUG', 'SEP', 'OCT', 'DEC', 'SEP']
    mes = ['FEV', 'ABR', 'MAI', 'AGO', 'SET', 'OUT', 'DEZ', 'STO']
    for m in mes:
        if m in txt:
            idx=mes.index(m)
            txt = re.sub(m,month[idx], txt)        
    x=re.search(r'\w{3}/\d{2}', txt)
    if x!= None:
        return x.group()
    
#aplicando as correções
df['data_produto'] = df['produto'].apply(data_produto)
df['data_produto'] = pd.to_datetime(df['produto'].apply(data_produto), format='%b/%y')
df['data_produto'] = df['data_produto'].apply(lambda x: datetime.date(x))
df['data_produto'].fillna('Nao identificado', inplace=True)



#calculo de maturidade
date_start = datetime.strptime('2015-01-01 00:00:00','%Y-%m-%d %H:%M:%S')

df['maturidade'] = ''

df['maturidade'] = np.where(((df['data_produto']< datetime.date(date_start))),'Não identificado', df['maturidade'])
df['maturidade'] = np.where((df['data_produto'] >= datetime.date(date_start)) & (df['data_produto'] < df['mes_ano_op']),'M-', df['maturidade'])
df['maturidade'] = np.where((df['data_produto'] == df['mes_ano_op']),'M0', df['maturidade'])
df['maturidade'] = np.where((df['data_produto'] > df['mes_ano_op']) & (df['data_produto'] <= (df['mes_ano_op'] + relativedelta(months=1))),'M1', df['maturidade'])
df['maturidade'] = np.where((df['data_produto'] > (df['mes_ano_op'] + relativedelta(months=1))) & (df['data_produto'] <= (df['mes_ano_op'] + relativedelta(months=2))),'M2', df['maturidade'])
df['maturidade'] = np.where((df['data_produto'] > (df['mes_ano_op'] + relativedelta(months=2))) & (df['data_produto'] <= (df['mes_ano_op'] + relativedelta(months=3))),'M3', df['maturidade'])
df['maturidade'] = np.where((df['data_produto'] > (df['mes_ano_op'] + relativedelta(months=3))) & (df['data_produto'] <= (df['mes_ano_op'] + relativedelta(months=4))),'M4', df['maturidade'])
df['maturidade'] = np.where((df['data_produto'] > (df['mes_ano_op']+ relativedelta(months=4))) , 'M5', df['maturidade'])


# In[9]:


#diferença de preço com a operação anterior
df = df.sort_values(by=['produto', 'data_completa'])

df['delta_op']=df.groupby(['tipo', 'produto', 'maturidade'])['preco'].diff()
#df['delta_op']=df.groupby(['tipo', 'produto'])['preco'].diff()
df['delta_op'] = df['delta_op'].fillna(0)


# In[10]:


#cáclulo da mediana em um dia
median = df.groupby(['tipo', 'produto', 'data'])['preco'].median()
median = median.reset_index()
median.rename(columns={'preco': 'mediana'}, inplace = True)

df = pd.merge(df, median, on=['tipo', 'produto', 'data'], how='left')


# # **Testes de Consistência**

# Checar se há operações registradas antes/depois do horário previsto de início/fim das operações. Pelas regras de negócio, é esperado operações fora do intervalo 09h-18h para Boleta

# In[11]:


st.subheader('Validação de datas e horários')

#checar se há datas inferiores a data de corte inicial ou maiores que a data atual
date_start = datetime.strptime('2017-01-01 00:00:00','%Y-%m-%d %H:%M:%S')
date_now = datetime.now()
st.write(f'Limites de data esperados:  Início = {date_start} | Fim = {date_now}')

df['flag_date'] = 0
df['flag_date'] = np.where((df['data_completa'] < date_start) | (df['data_completa'] > date_now), 1, df['flag_date'])

if  df['flag_date'].sum() > 1:

    df['flag_datetime'] = np.where((df['data_completa'] < date_start) | (df['data_completa'] > date_now), 1, 0)
    check_datas = 'Sim'
    qtd_datas = df['flag_datetime'].sum()

    st.write('Há registros que violam os limites de data:')
    st.write(df.query('flag_date ==1'))
    
else:
    st.write('Datas dentro dos limites esperados')
    check_datas = 'Não'
    qtd_datas = 0
#se não retornar itens, não há registros que violem as datas esperadas


# In[12]:


#Checar se há operações registradas antes/depois do horário previsto de início/fim das operações.
#Pelas regras de negócio, é esperado operações fora do intervalo 09h-18h para Boleta
st.write('')
time_open = datetime.strptime('08:30:00','%H:%M:%S')
time_open = datetime.time(time_open)
time_close = datetime.strptime('18:30:00','%H:%M:%S')
time_close = datetime.time(time_close)
st.write(f'Limites de horário esperados: Início = {time_open} | Fim = {time_close}')
df['flag_timeopen'] = 0
df['flag_timeclose'] = 0

#verificação para Balcao
df['flag_timeopen'] = np.where((df['local'] != 'Boleta' ) & (df['time'] < time_open) & (df['ano_op'] > 2019), 1, df['flag_timeopen'])
df['flag_timeclose'] = np.where((df['local'] != 'Boleta' ) & (df['time'] > time_close) & (df['ano_op'] > 2019), 1, df['flag_timeclose'])

if df['flag_timeopen'].sum() > 0:
    check_open = 'Sim'
    qtd_open = df['flag_timeopen'].sum()
    percent = round((qtd_open/df['produto'].count())*100,2)

    st.write(f'Há {qtd_open} ({percent}%) registros que violam os limites de horário inicial:')
    st.write(df.query('flag_timeopen == 1'))
else:
    check_open = 'Não'
    qtd_open = 0
 

if df['flag_timeclose'].sum() > 0:
    check_close = 'Sim'
    qtd_close = df['flag_timeclose'].sum()
    percent = round((qtd_open/df['produto'].count())*100,2)

    st.write(f'Há {qtd_open} ({percent}%) registros que violam os limites de horário inicial:')
    st.write(df.query('flag_timeclose == 1'))
else:
    check_close = 'Não'
    qtd_close = 0


if df['flag_timeclose'].sum() == 0 and df['flag_timeopen'].sum() == 0:
    st.write('Horários dentro dos limites esperados')
    qtd_horas = 0
    check_horas = 'Não'
    


# # **Análises Relacionais**

# In[13]:


st.header('Análises Relacionais')
st.subheader('Variações de preço por produto')


# In[14]:


#teste para detecção de possíveis anomalias com IQR
# 1 - diferença de preços das ops diárias

Q1=0.15
Q3=0.85
df2=df[(df['delta_op'] != 0) & (df['local'] == 'Balcao')]

Q1_spread0 = df2[((df2['tipo']=='Spread')&(df2['maturidade']=='M0'))].quantile(Q1)
Q3_spread0 = df2[((df2['tipo']=='Spread')&(df2['maturidade']=='M0'))].quantile(Q3)
IQR_spread0 = Q3_spread0 - Q1_spread0

Q1_spread1 = df2[((df2['tipo']=='Spread')&(df2['maturidade']=='M1'))].quantile(Q1)
Q3_spread1 = df2[((df2['tipo']=='Spread')&(df2['maturidade']=='M1'))].quantile(Q3)
IQR_spread1 = Q3_spread1 - Q1_spread1

Q1_spread2 = df2[((df2['tipo']=='Spread')&(df2['maturidade']=='M2'))].quantile(Q1)
Q3_spread2 = df2[((df2['tipo']=='Spread')&(df2['maturidade']=='M2'))].quantile(Q3)
IQR_spread2 = Q3_spread2 - Q1_spread2

Q1_spread3 = df2[((df2['tipo']=='Spread')&(df2['maturidade']=='M3'))].quantile(Q1)
Q3_spread3 = df2[((df2['tipo']=='Spread')&(df2['maturidade']=='M3'))].quantile(Q3)
IQR_spread3 = Q3_spread3 - Q1_spread3

Q1_spread4 = df2[((df2['tipo']=='Spread')&(df2['maturidade']=='M4'))].quantile(Q1)
Q3_spread4 = df2[((df2['tipo']=='Spread')&(df2['tipo']=='M4'))].quantile(Q3)
IQR_spread4 = Q3_spread4 - Q1_spread4

Q1_spread5 = df2[((df2['tipo']=='Spread')&(df2['maturidade']=='M5'))].quantile(Q1)
Q3_spread5 = df2[((df2['tipo']=='Spread')&(df2['maturidade']=='M5'))].quantile(Q3)
IQR_spread5 = Q3_spread5 - Q1_spread5

df['flag_preco1'] = 0

df['flag_preco1'] = np.where(((df['tipo']=='Spread') & (df['maturidade']=='M0') & (df['delta_op'] < (Q1_spread0[5] - 1.5 * IQR_spread0[5]))) | ((df['tipo']=='Spread') & (df['maturidade']=='M0') & (df['delta_op'] > (Q3_spread0[5] + 1.5 * IQR_spread0[5]))) , 1, df['flag_preco1'])
df['flag_preco1'] = np.where(((df['tipo']=='Spread') & (df['maturidade']=='M1') & (df['delta_op'] < (Q1_spread1[5] - 1.5 * IQR_spread1[5]))) | ((df['tipo']=='Spread') & (df['maturidade']=='M1') & (df['delta_op'] > (Q3_spread1[5] + 1.5 * IQR_spread1[5]))) , 1, df['flag_preco1'])
df['flag_preco1'] = np.where(((df['tipo']=='Spread') & (df['maturidade']=='M2') & (df['delta_op'] < (Q1_spread2[5] - 1.5 * IQR_spread2[5]))) | ((df['tipo']=='Spread') & (df['maturidade']=='M2') & (df['delta_op'] > (Q3_spread2[5] + 1.5 * IQR_spread2[5]))) , 1, df['flag_preco1'])
df['flag_preco1'] = np.where(((df['tipo']=='Spread') & (df['maturidade']=='M3') & (df['delta_op'] < (Q1_spread3[5] - 1.5 * IQR_spread3[5]))) | ((df['tipo']=='Spread') & (df['maturidade']=='M3') & (df['delta_op'] > (Q3_spread3[5] + 1.5 * IQR_spread3[5]))) , 1, df['flag_preco1'])
df['flag_preco1'] = np.where(((df['tipo']=='Spread') & (df['maturidade']=='M4') & (df['delta_op'] < (Q1_spread4[5] - 1.5 * IQR_spread4[5]))) | ((df['tipo']=='Spread') & (df['maturidade']=='M4') & (df['delta_op'] > (Q3_spread4[5] + 1.5 * IQR_spread4[5]))) , 1, df['flag_preco1'])
df['flag_preco1'] = np.where(((df['tipo']=='Spread') & (df['maturidade']=='M5') & (df['delta_op'] < (Q1_spread5[5] - 1.5 * IQR_spread5[5]))) | ((df['tipo']=='Spread') & (df['maturidade']=='M5') & (df['delta_op'] > (Q3_spread5[5] + 1.5 * IQR_spread5[5]))) , 1, df['flag_preco1'])


Q1_pld0 = df2[((df2['tipo']=='PLD')&(df2['maturidade']=='M0'))].quantile(Q1)
Q3_pld0 = df2[((df2['tipo']=='PLD')&(df2['maturidade']=='M0'))].quantile(Q3)
IQR_pld0 = Q3_pld0 - Q1_pld0

Q1_pld1 = df2[((df2['tipo']=='PLD')&(df2['maturidade']=='M1'))].quantile(Q1)
Q3_pld1 = df2[((df2['tipo']=='PLD')&(df2['maturidade']=='M1'))].quantile(Q3)
IQR_pld1 = Q3_pld1 - Q1_pld1

Q1_pld2 = df2[((df2['tipo']=='PLD')&(df2['maturidade']=='M2'))].quantile(Q1)
Q3_pld2 = df2[((df2['tipo']=='PLD')&(df2['maturidade']=='M2'))].quantile(Q3)
IQR_pld2 = Q3_pld2 - Q1_pld2

Q1_pld3 = df2[((df2['tipo']=='PLD')&(df2['maturidade']=='M3'))].quantile(Q1)
Q3_pld3 = df2[((df2['tipo']=='PLD')&(df2['maturidade']=='M3'))].quantile(Q3)
IQR_pld3 = Q3_pld3 - Q1_pld3

Q1_pld4 = df2[((df2['tipo']=='PLD')&(df2['maturidade']=='M4'))].quantile(Q1)
Q3_pld4 = df2[((df2['tipo']=='PLD')&(df2['maturidade']=='M4'))].quantile(Q3)
IQR_pld4 = Q3_pld4 - Q1_pld4

Q1_pld5 = df2[((df2['tipo']=='PLD')&(df2['maturidade']=='M5'))].quantile(Q1)
Q3_pld5 = df2[((df2['tipo']=='PLD')&(df2['maturidade']=='M5'))].quantile(Q3)
IQR_pld5 = Q3_pld5 - Q1_pld5


df['flag_preco1'] = np.where(((df['tipo']=='PLD') & (df['maturidade']=='M0') & (df['delta_op'] < (Q1_pld0[5] - 1.5 * IQR_pld0[5]))) | ((df['tipo']=='PLD') & (df['maturidade']=='M0') & (df['delta_op'] > (Q3_pld0[5] + 1.5 * IQR_pld0[5]))) , 1, df['flag_preco1'])
df['flag_preco1'] = np.where(((df['tipo']=='PLD') & (df['maturidade']=='M1') & (df['delta_op'] < (Q1_pld1[5] - 1.5 * IQR_pld1[5]))) | ((df['tipo']=='PLD') & (df['maturidade']=='M1') & (df['delta_op'] > (Q3_pld1[5] + 1.5 * IQR_pld1[5]))) , 1, df['flag_preco1'])
df['flag_preco1'] = np.where(((df['tipo']=='PLD') & (df['maturidade']=='M2') & (df['delta_op'] < (Q1_pld2[5] - 1.5 * IQR_pld2[5]))) | ((df['tipo']=='PLD') & (df['maturidade']=='M2') & (df['delta_op'] > (Q3_pld2[5] + 1.5 * IQR_pld2[5]))) , 1, df['flag_preco1'])
df['flag_preco1'] = np.where(((df['tipo']=='PLD') & (df['maturidade']=='M3') & (df['delta_op'] < (Q1_pld3[5] - 1.5 * IQR_pld3[5]))) | ((df['tipo']=='PLD') & (df['maturidade']=='M3') & (df['delta_op'] > (Q3_pld3[5] + 1.5 * IQR_pld3[5]))) , 1, df['flag_preco1'])
df['flag_preco1'] = np.where(((df['tipo']=='PLD') & (df['maturidade']=='M4') & (df['delta_op'] < (Q1_pld4[5] - 1.5 * IQR_pld4[5]))) | ((df['tipo']=='PLD') & (df['maturidade']=='M4') & (df['delta_op'] > (Q3_pld4[5] + 1.5 * IQR_pld4[5]))) , 1, df['flag_preco1'])
df['flag_preco1'] = np.where(((df['tipo']=='PLD') & (df['maturidade']=='M5') & (df['delta_op'] < (Q1_pld5[5] - 1.5 * IQR_pld5[5]))) | ((df['tipo']=='PLD') & (df['maturidade']=='M5') & (df['delta_op'] > (Q3_pld5[5] + 1.5 * IQR_pld5[5]))) , 1, df['flag_preco1'])


Q1_pf0 = df2[((df2['tipo']=='Preco Fixo')&(df2['maturidade']=='M0'))].quantile(Q1)
Q3_pf0 = df2[((df2['tipo']=='Preco Fixo')&(df2['maturidade']=='M0'))].quantile(Q3)
IQR_pf0 = Q3_pf0 - Q1_pf0

Q1_pf1 = df2[((df2['tipo']=='Preco Fixo')&(df2['maturidade']=='M1'))].quantile(Q1)
Q3_pf1 = df2[((df2['tipo']=='Preco Fixo')&(df2['maturidade']=='M1'))].quantile(Q3)
IQR_pf1 = Q3_pf1 - Q1_pf1

Q1_pf2 = df2[((df2['tipo']=='Preco Fixo')&(df2['maturidade']=='M2'))].quantile(Q1)
Q3_pf2 = df2[((df2['tipo']=='Preco Fixo')&(df2['maturidade']=='M2'))].quantile(Q3)
IQR_pf2 = Q3_pf2 - Q1_pf2

Q1_pf3 = df2[((df2['tipo']=='Preco Fixo')&(df2['maturidade']=='M3'))].quantile(Q1)
Q3_pf3 = df2[((df2['tipo']=='Preco Fixo')&(df2['maturidade']=='M3'))].quantile(Q3)
IQR_pf3 = Q3_pf3 - Q1_pf3

Q1_pf4 = df2[((df2['tipo']=='Preco Fixo')&(df2['maturidade']=='M4'))].quantile(Q1)
Q3_pf4 = df2[((df2['tipo']=='Preco Fixo')&(df2['maturidade']=='M4'))].quantile(Q3)
IQR_pf4 = Q3_pf4 - Q1_pf4

Q1_pf5 = df2[((df2['tipo']=='Preco Fixo')&(df2['maturidade']=='M5'))].quantile(Q1)
Q3_pf5 = df2[((df2['tipo']=='Preco Fixo')&(df2['maturidade']=='M5'))].quantile(Q3)
IQR_pf5 = Q3_pf5 - Q1_pf5



df['flag_preco1'] = np.where(((df['tipo']=='Preco Fixo') & (df['maturidade']=='M0') & (df['delta_op'] < (Q1_pf0[5] - 1.5 * IQR_pf0[5]))) | ((df['tipo']=='Preco Fixo') & (df['maturidade']=='M0') & (df['delta_op'] > (Q3_pf0[5] + 1.5 * IQR_pf0[5]))) , 1, df['flag_preco1'])
df['flag_preco1'] = np.where(((df['tipo']=='Preco Fixo') & (df['maturidade']=='M1') & (df['delta_op'] < (Q1_pf1[5] - 1.5 * IQR_pf1[5]))) | ((df['tipo']=='Preco Fixo') & (df['maturidade']=='M1') & (df['delta_op'] > (Q3_pf1[5] + 1.5 * IQR_pf1[5]))) , 1, df['flag_preco1'])
df['flag_preco1'] = np.where(((df['tipo']=='Preco Fixo') & (df['maturidade']=='M2') & (df['delta_op'] < (Q1_pf2[5] - 1.5 * IQR_pf2[5]))) | ((df['tipo']=='Preco Fixo') & (df['maturidade']=='M2') & (df['delta_op'] > (Q3_pf2[5] + 1.5 * IQR_pf2[5]))) , 1, df['flag_preco1'])
df['flag_preco1'] = np.where(((df['tipo']=='Preco Fixo') & (df['maturidade']=='M3') & (df['delta_op'] < (Q1_pf3[5] - 1.5 * IQR_pf3[5]))) | ((df['tipo']=='Preco Fixo') & (df['maturidade']=='M3') & (df['delta_op'] > (Q3_pf3[5] + 1.5 * IQR_pf3[5]))) , 1, df['flag_preco1'])
df['flag_preco1'] = np.where(((df['tipo']=='Preco Fixo') & (df['maturidade']=='M4') & (df['delta_op'] < (Q1_pf4[5] - 1.5 * IQR_pf4[5]))) | ((df['tipo']=='Preco Fixo') & (df['maturidade']=='M4') & (df['delta_op'] > (Q3_pf4[5] + 1.5 * IQR_pf4[5]))) , 1, df['flag_preco1'])
df['flag_preco1'] = np.where(((df['tipo']=='Preco Fixo') & (df['maturidade']=='M5') & (df['delta_op'] < (Q1_pf5[5] - 1.5 * IQR_pf5[5]))) | ((df['tipo']=='Preco Fixo') & (df['maturidade']=='M5') & (df['delta_op'] > (Q3_pf5[5] + 1.5 * IQR_pf5[5]))) , 1, df['flag_preco1'])


# In[15]:


# teste 2 - usando a mediana
df['delta_mediana'] = df['preco'] - df['mediana']

Q1=0.15
Q3=0.85
df3=df[(df['delta_op'] != 0) & (df['local'] == 'Balcao')]

Q1_spread0 = df3[((df3['tipo']=='Spread')&(df3['maturidade']=='M0'))].quantile(Q1)
Q3_spread0 = df3[((df3['tipo']=='Spread')&(df3['maturidade']=='M0'))].quantile(Q3)
IQR_spread0 = Q3_spread0 - Q1_spread0

Q1_spread1 = df3[((df3['tipo']=='Spread')&(df3['maturidade']=='M1'))].quantile(Q1)
Q3_spread1 = df3[((df3['tipo']=='Spread')&(df3['maturidade']=='M1'))].quantile(Q3)
IQR_spread1 = Q3_spread1 - Q1_spread1

Q1_spread2 = df3[((df3['tipo']=='Spread')&(df3['maturidade']=='M2'))].quantile(Q1)
Q3_spread2 = df3[((df3['tipo']=='Spread')&(df3['maturidade']=='M2'))].quantile(Q3)
IQR_spread2 = Q3_spread2 - Q1_spread2

Q1_spread3 = df3[((df3['tipo']=='Spread')&(df3['maturidade']=='M3'))].quantile(Q1)
Q3_spread3 = df3[((df3['tipo']=='Spread')&(df3['maturidade']=='M3'))].quantile(Q3)
IQR_spread3 = Q3_spread3 - Q1_spread3

Q1_spread4 = df3[((df3['tipo']=='Spread')&(df3['maturidade']=='M4'))].quantile(Q1)
Q3_spread4 = df3[((df3['tipo']=='Spread')&(df3['tipo']=='M4'))].quantile(Q3)
IQR_spread4 = Q3_spread4 - Q1_spread4

Q1_spread5 = df3[((df3['tipo']=='Spread')&(df3['maturidade']=='M5'))].quantile(Q1)
Q3_spread5 = df3[((df3['tipo']=='Spread')&(df3['maturidade']=='M5'))].quantile(Q3)
IQR_spread5 = Q3_spread5 - Q1_spread5


df['flag_preco2'] = 0

df['flag_preco2'] = np.where(((df['tipo']=='Spread') & (df['maturidade']=='M0') & (df['delta_mediana'] < (Q1_spread0[11] - 1.5 * IQR_spread0[11]))) | ((df['tipo']=='Spread') & (df['maturidade']=='M0') & (df['delta_mediana'] > (Q3_spread0[11] + 1.5 * IQR_spread0[11]))) , 1, df['flag_preco2'])
df['flag_preco2'] = np.where(((df['tipo']=='Spread') & (df['maturidade']=='M1') & (df['delta_mediana'] < (Q1_spread1[11] - 1.5 * IQR_spread1[11]))) | ((df['tipo']=='Spread') & (df['maturidade']=='M1') & (df['delta_mediana'] > (Q3_spread1[11] + 1.5 * IQR_spread1[11]))) , 1, df['flag_preco2'])
df['flag_preco2'] = np.where(((df['tipo']=='Spread') & (df['maturidade']=='M2') & (df['delta_mediana'] < (Q1_spread2[11] - 1.5 * IQR_spread2[11]))) | ((df['tipo']=='Spread') & (df['maturidade']=='M2') & (df['delta_mediana'] > (Q3_spread2[11] + 1.5 * IQR_spread2[11]))) , 1, df['flag_preco2'])
df['flag_preco2'] = np.where(((df['tipo']=='Spread') & (df['maturidade']=='M3') & (df['delta_mediana'] < (Q1_spread3[11] - 1.5 * IQR_spread3[11]))) | ((df['tipo']=='Spread') & (df['maturidade']=='M3') & (df['delta_mediana'] > (Q3_spread3[11] + 1.5 * IQR_spread3[11]))) , 1, df['flag_preco2'])
df['flag_preco2'] = np.where(((df['tipo']=='Spread') & (df['maturidade']=='M4') & (df['delta_mediana'] < (Q1_spread4[11] - 1.5 * IQR_spread4[11]))) | ((df['tipo']=='Spread') & (df['maturidade']=='M4') & (df['delta_mediana'] > (Q3_spread4[11] + 1.5 * IQR_spread4[11]))) , 1, df['flag_preco2'])
df['flag_preco2'] = np.where(((df['tipo']=='Spread') & (df['maturidade']=='M5') & (df['delta_mediana'] < (Q1_spread5[11] - 1.5 * IQR_spread5[11]))) | ((df['tipo']=='Spread') & (df['maturidade']=='M5') & (df['delta_mediana'] > (Q3_spread5[11] + 1.5 * IQR_spread5[11]))) , 1, df['flag_preco2'])

Q1_pld0 = df3[((df3['tipo']=='PLD')&(df3['maturidade']=='M0'))].quantile(Q1)
Q3_pld0 = df3[((df3['tipo']=='PLD')&(df3['maturidade']=='M0'))].quantile(Q3)
IQR_pld0 = Q3_pld0 - Q1_pld0

Q1_pld1 = df3[((df3['tipo']=='PLD')&(df3['maturidade']=='M1'))].quantile(Q1)
Q3_pld1 = df3[((df3['tipo']=='PLD')&(df3['maturidade']=='M1'))].quantile(Q3)
IQR_pld1 = Q3_pld1 - Q1_pld1

Q1_pld2 = df3[((df3['tipo']=='PLD')&(df3['maturidade']=='M2'))].quantile(Q1)
Q3_pld2 = df3[((df3['tipo']=='PLD')&(df3['maturidade']=='M2'))].quantile(Q3)
IQR_pld2 = Q3_pld2 - Q1_pld2

Q1_pld3 = df3[((df3['tipo']=='PLD')&(df3['maturidade']=='M3'))].quantile(Q1)
Q3_pld3 = df3[((df3['tipo']=='PLD')&(df3['maturidade']=='M3'))].quantile(Q3)
IQR_pld3 = Q3_pld3 - Q1_pld3

Q1_pld4 = df3[((df3['tipo']=='PLD')&(df3['maturidade']=='M4'))].quantile(Q1)
Q3_pld4 = df3[((df3['tipo']=='PLD')&(df3['maturidade']=='M4'))].quantile(Q3)
IQR_pld4 = Q3_pld4 - Q1_pld4

Q1_pld5 = df3[((df3['tipo']=='PLD')&(df3['maturidade']=='M5'))].quantile(Q1)
Q3_pld5 = df3[((df3['tipo']=='PLD')&(df3['maturidade']=='M5'))].quantile(Q3)
IQR_pld5 = Q3_pld5 - Q1_pld5


df['flag_preco2'] = np.where(((df['tipo']=='PLD') & (df['maturidade']=='M0') & (df['delta_mediana'] < (Q1_pld0[11] - 1.5 * IQR_pld0[11]))) | ((df['tipo']=='PLD') & (df['maturidade']=='M0') & (df['delta_mediana'] > (Q3_pld0[11] + 1.5 * IQR_pld0[11]))) , 1, df['flag_preco2'])
df['flag_preco2'] = np.where(((df['tipo']=='PLD') & (df['maturidade']=='M1') & (df['delta_mediana'] < (Q1_pld1[11] - 1.5 * IQR_pld1[11]))) | ((df['tipo']=='PLD') & (df['maturidade']=='M1') & (df['delta_mediana'] > (Q3_pld1[11] + 1.5 * IQR_pld1[11]))) , 1, df['flag_preco2'])
df['flag_preco2'] = np.where(((df['tipo']=='PLD') & (df['maturidade']=='M2') & (df['delta_mediana'] < (Q1_pld2[11] - 1.5 * IQR_pld2[11]))) | ((df['tipo']=='PLD') & (df['maturidade']=='M2') & (df['delta_mediana'] > (Q3_pld2[11] + 1.5 * IQR_pld2[11]))) , 1, df['flag_preco2'])
df['flag_preco2'] = np.where(((df['tipo']=='PLD') & (df['maturidade']=='M3') & (df['delta_mediana'] < (Q1_pld3[11] - 1.5 * IQR_pld3[11]))) | ((df['tipo']=='PLD') & (df['maturidade']=='M3') & (df['delta_mediana'] > (Q3_pld3[11] + 1.5 * IQR_pld3[11]))) , 1, df['flag_preco2'])
df['flag_preco2'] = np.where(((df['tipo']=='PLD') & (df['maturidade']=='M4') & (df['delta_mediana'] < (Q1_pld4[11] - 1.5 * IQR_pld4[11]))) | ((df['tipo']=='PLD') & (df['maturidade']=='M4') & (df['delta_mediana'] > (Q3_pld4[11] + 1.5 * IQR_pld4[11]))) , 1, df['flag_preco2'])
df['flag_preco2'] = np.where(((df['tipo']=='PLD') & (df['maturidade']=='M5') & (df['delta_mediana'] < (Q1_pld5[11] - 1.5 * IQR_pld5[11]))) | ((df['tipo']=='PLD') & (df['maturidade']=='M5') & (df['delta_mediana'] > (Q3_pld5[11] + 1.5 * IQR_pld5[11]))) , 1, df['flag_preco2'])


Q1_pf0 = df3[((df3['tipo']=='Preco Fixo')&(df3['maturidade']=='M0'))].quantile(Q1)
Q3_pf0 = df3[((df3['tipo']=='Preco Fixo')&(df3['maturidade']=='M0'))].quantile(Q3)
IQR_pf0 = Q3_pf0 - Q1_pf0

Q1_pf1 = df3[((df3['tipo']=='Preco Fixo')&(df3['maturidade']=='M1'))].quantile(Q1)
Q3_pf1 = df3[((df3['tipo']=='Preco Fixo')&(df3['maturidade']=='M1'))].quantile(Q3)
IQR_pf1 = Q3_pf1 - Q1_pf1

Q1_pf2 = df3[((df3['tipo']=='Preco Fixo')&(df3['maturidade']=='M2'))].quantile(Q1)
Q3_pf2 = df3[((df3['tipo']=='Preco Fixo')&(df3['maturidade']=='M2'))].quantile(Q3)
IQR_pf2 = Q3_pf2 - Q1_pf2

Q1_pf3 = df3[((df3['tipo']=='Preco Fixo')&(df3['maturidade']=='M3'))].quantile(Q1)
Q3_pf3 = df3[((df3['tipo']=='Preco Fixo')&(df3['maturidade']=='M3'))].quantile(Q3)
IQR_pf3 = Q3_pf3 - Q1_pf3

Q1_pf4 = df3[((df3['tipo']=='Preco Fixo')&(df3['maturidade']=='M4'))].quantile(Q1)
Q3_pf4 = df3[((df3['tipo']=='Preco Fixo')&(df3['maturidade']=='M4'))].quantile(Q3)
IQR_pf4 = Q3_pf4 - Q1_pf4

Q1_pf5 = df3[((df3['tipo']=='Preco Fixo')&(df3['maturidade']=='M5'))].quantile(Q1)
Q3_pf5 = df3[((df3['tipo']=='Preco Fixo')&(df3['maturidade']=='M5'))].quantile(Q3)
IQR_pf5 = Q3_pf5 - Q1_pf5

df['flag_preco2'] = np.where(((df['tipo']=='Preco Fixo') & (df['maturidade']=='M0') & (df['delta_mediana'] < (Q1_pf0[11] - 1.5 * IQR_pf0[11]))) | ((df['tipo']=='Preco Fixo') & (df['maturidade']=='M0') & (df['delta_mediana'] > (Q3_pf0[11] + 1.5 * IQR_pf0[11]))) , 1, df['flag_preco2'])
df['flag_preco2'] = np.where(((df['tipo']=='Preco Fixo') & (df['maturidade']=='M1') & (df['delta_mediana'] < (Q1_pf1[11] - 1.5 * IQR_pf1[11]))) | ((df['tipo']=='Preco Fixo') & (df['maturidade']=='M1') & (df['delta_mediana'] > (Q3_pf1[11] + 1.5 * IQR_pf1[11]))) , 1, df['flag_preco2'])
df['flag_preco2'] = np.where(((df['tipo']=='Preco Fixo') & (df['maturidade']=='M2') & (df['delta_mediana'] < (Q1_pf2[11] - 1.5 * IQR_pf2[11]))) | ((df['tipo']=='Preco Fixo') & (df['maturidade']=='M2') & (df['delta_mediana'] > (Q3_pf2[11] + 1.5 * IQR_pf2[11]))) , 1, df['flag_preco2'])
df['flag_preco2'] = np.where(((df['tipo']=='Preco Fixo') & (df['maturidade']=='M3') & (df['delta_mediana'] < (Q1_pf3[11] - 1.5 * IQR_pf3[11]))) | ((df['tipo']=='Preco Fixo') & (df['maturidade']=='M3') & (df['delta_mediana'] > (Q3_pf3[11] + 1.5 * IQR_pf3[11]))) , 1, df['flag_preco2'])
df['flag_preco2'] = np.where(((df['tipo']=='Preco Fixo') & (df['maturidade']=='M4') & (df['delta_mediana'] < (Q1_pf4[11] - 1.5 * IQR_pf4[11]))) | ((df['tipo']=='Preco Fixo') & (df['maturidade']=='M4') & (df['delta_mediana'] > (Q3_pf4[11] + 1.5 * IQR_pf4[11]))) , 1, df['flag_preco2'])
df['flag_preco2'] = np.where(((df['tipo']=='Preco Fixo') & (df['maturidade']=='M5') & (df['delta_mediana'] < (Q1_pf5[11] - 1.5 * IQR_pf5[11]))) | ((df['tipo']=='Preco Fixo') & (df['maturidade']=='M5') & (df['delta_mediana'] > (Q3_pf5[11] + 1.5 * IQR_pf5[11]))) , 1, df['flag_preco2'])


# In[16]:


df['flag_algoritmo'] = 0
df['flag_algoritmo'] = np.where((df['flag_date'] != 0) | (df['flag_timeopen'] != 0) | (df['flag_timeclose'] != 0) | (df['flag_preco1'] != 0) | (df['flag_preco2'] != 0), 1, df['flag_algoritmo'])
df['flag_user'] = df['flag_algoritmo']


# In[17]:


if (df['flag_preco1'] == 1 ).any() or (df['flag_preco2'] == 1 ).any():
    check_preco = 'Sim'
    result1 = df.groupby(['maturidade']).agg({'flag_preco1':np.sum})
    result2 = df.groupby(['maturidade']).agg({'flag_preco2':np.sum})
    st.write('Resultados do Teste 1:')
    st.write(result1)
    st.write(df.query('flag_preco1 == 1'))
    st.write('Resultados do Teste 2:')
    st.write(result2)
    st.write(df.query('flag_preco2 == 1'))
else:
    check_preco = 'Não'
    qtd_preco = 0
    st.write('Variações de preço dentro dos limites esperados.') 


# In[18]:


st.subheader('Análises gráficas')

#!pip install plotly
import plotly.offline as py
import plotly.graph_objs as go
py.init_notebook_mode(connected=True)

sns.set_style('darkgrid')

sec_expander = st.expander(label='Visualizar lista de produtos')
with sec_expander:
    'Selecione um produto para visualizar a variação de preço ao longo do tempo.'
    for prod in df['produto'].unique():
        check = st.checkbox(prod)
        if check:
            validacao = df[(df['produto'] == prod)] 
            trace1 = go.Scatter(x = validacao['data_completa'],
                   y = validacao['preco'],
                   mode = 'lines',
                   name = prod,
                   line = {'dash': 'dash'})
    
            trace2 = go.Scatter(x = validacao['data_completa'],
                   y = validacao['preco'],
                   mode = 'markers',
                   name = 'possíveis outliers - em amarelo',
                   marker = dict(color = validacao['flag_algoritmo'])) 
            data = [trace1, trace2]

            layout = go.Layout(title=prod,
                   yaxis={'title':'preço'},
                   xaxis={'title': 'data/hora'})

            fig = go.Figure(data=data, layout=layout)
            st.plotly_chart(fig)  


# In[19]:


tag=list(tags)
tag.append('flag_tipo')
logs = pd.DataFrame(columns = tag)


# In[20]:


#registro de todas as possíveis anomalias
tipo1 = df.query('flag_date ==1')
tipo1 = tipo1[list(tags)]
tipo1['flag_tipo'] = 1
logs=logs.append(tipo1,ignore_index=True)

tipo2 = df.query('flag_timeopen == 1')
tipo2 = tipo2[list(tags)]
tipo2['flag_tipo'] = 2
logs=logs.append(tipo2,ignore_index=True)

tipo3 = df.query('flag_timeclose == 1')
tipo3 = tipo3[list(tags)]
tipo3['flag_tipo'] = 3
logs=logs.append(tipo3,ignore_index=True)

tipo4 = df.query('flag_preco1 == 1')
tipo4 = tipo4[list(tags)]
tipo4['flag_tipo'] = 4
logs=logs.append(tipo4,ignore_index=True)

tipo5 = df.query('flag_preco2 == 1')
tipo5 = tipo5[list(tags)]
tipo5['flag_tipo'] = 5
logs=logs.append(tipo5,ignore_index=True)

logs = logs[['id','data_completa', 'flag_tipo']]


# In[21]:


#limpando o df 
tags=list(tags)
tags.append('maturidade')
tags.append('flag_algoritmo')
tags.append('flag_user')
df = df[tags]

if df['flag_algoritmo'].sum() != 0:
    check_anomalias = 'Sim'


# In[22]:


resumo = {'Item': ['Dados duplicados', 'Dados nulos', 'Possíveis anomalias'],
           'Anomalias detectadas?': [check_duplicados, check_null, check_anomalias],
           'Quantidade de registros afetados': [qtd_duplicados, qtd_null, df['flag_algoritmo'].sum()]
}


# # **Análise Exploratória dos Dados**

# In[23]:


# descritivo dos dados

st.header('Data profiling')

from pandas_profiling import ProfileReport
profile = ProfileReport(df, title=' ', config_file='volt_config.yaml')


# In[24]:


from streamlit_pandas_profiling import st_profile_report
st_profile_report(profile)


# In[25]:


#exportar o dataset tratado
def get_download(df, arq):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode() 
    href = f'<a href="data:file/csv;base64,{b64}" download="'+arq+'.csv">Download</a>'
    return href

st.markdown(get_download(df, 'precos_bbce'), unsafe_allow_html=True)

