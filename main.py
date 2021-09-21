#!/usr/bin/env python
# coding: utf-8

# SCRIPT EM DESENVOLVIMENTO
# 
# notes to self: 
# corrigir a formatação dos horários e incluir tolerância
# conectar com bd
# incluir verificação de alterações abruptas 
# 
# no relatório html
#  incluir timeline por feat.
#  editar bins 
#  acrescentar verificação de datas/horários com as condições inicio/fim como parâmentros

# In[76]:

import matplotlib
from matplotlib.backends.backend_agg import RendererAgg
import pandas as pd 
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
from matplotlib.figure import Figure
import base64

st.set_page_config(layout="wide")


# In[3]:


st.title('Data Quality & Assurance')


# # **Leitura do dataset e testes de formatação**

# In[25]:

#data = st.file_uploader('Escolha o dataset (.csv)', type = 'csv')
#if data is not None:
#    df = pd.read_csv(data)


st.header('Testes de Formatação')


# In[ ]:


df = pd.read_csv('Historico_BBCE.csv', sep=',') 


# In[42]:


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


# In[6]:


#corrigindo os tipos
df['tend'] = df['tend'].astype('category',copy=False)
df['tipo'] = df['tipo'].astype('category',copy=False)
df['produto'] = df['produto'].astype('category',copy=False)
df['local'] = df['local'].astype('string',copy=False)
df['qtde_mwm'] = df['qtde_mwm'].astype('float',copy=False)
df['qtde_mwh'] = df['qtde_mwh'].astype('float',copy=False)
df['data_completa'] = pd.to_datetime(df['data_completa']) #'%m-%d-%Y %I:%M%p'
df['data'] = pd.to_datetime(df['data'], format='%m/%d/%Y')
df['time'] = pd.to_datetime(df['time'], format='%H:%M:%S')

with row3_2, _lock:
    st.write('Formatação Corrigida')
    buffer = io.StringIO()
    df.info(buf=buffer)
    s = buffer.getvalue() 
    with open("df_info.txt", "w", encoding="utf-8") as f:
        st.text(s)


# In[81]:


#coluna para marcar anomalias - Registro com anomalia/outlier = 1
df['flag'] = 0


# # **Testes de Consistência**

# Checar se há operações registradas antes/depois do horário previsto de início/fim das operações. Pelas regras de negócio, é esperado operações fora do intervalo 09h-18h para Boleta

# In[26]:


st.header('Testes de Consistência')


# In[8]:


date_start = datetime.strptime('2017-01-01 00:00:00','%Y-%m-%d %H:%M:%S')
date_now = datetime.now()
st.write('Limites de data esperados -> ' + 'Início: ' + str(date_start) + ' Fim: ' + str(date_now))


# In[49]:


date_mask=df[(df['data_completa'] < date_start) | (df['data_completa'] > date_now)]


# In[85]:


#checar se há datas inferiores a data de corte inicial ou maiores que a data atual
if  date_mask.shape[0] > 1:

    df['flag'] = np.where((df['data_completa'] < date_start) | (df['data_completa'] > date_now), 1, 0)

    st.write('Há registros que violam os limites de data:')
    st.write(date_mask)
    
else:
    st.write('Datas dentro dos limites esperados')
#se não retornar itens, não há registros que violem as datas esperadas

#df['flag'] == 1


# In[10]:


st.write('')
time_open = datetime.strptime('08:55:00','%H:%M:%S')
time_close = datetime.strptime('18:30:00','%H:%M:%S')
st.write('Limites de horário esperados -> ' + 'Início: ' + str(time_open) + ' Fim: ' + str(time_close))


# In[94]:


#verificação para Balcao
if (df['local'] != 'Boleta' ).any() & (df['time'] < time_open).any():

    df['flag'] = np.where((df['local'] != 'Boleta' ) & (df['time'] < time_open), 1, 0)
    time_mask_before = df[(df['local'] != 'Boleta' ) & (df['time'] < time_open)]

    st.write('Há ' + str(time_mask_before['time'].count()) + ' registros que violam os limites de horário inicial:')
    st.write(time_mask_before.sort_values(by=['time']))

else:
    st.write('Horários iniciais dentro do limite esperado')

#g = df[(df['flag'] == 1)]
#g


# In[95]:


if (df['local'] != 'Boleta' ).any() & (df['time'] > time_close).any():

    df['flag'] = np.where((df['local'] != 'Boleta' ) & (df['time'] > time_close), 1, 0)
    time_mask_after = df[(df['local'] != 'Boleta' ) & (df['time'] > time_close)]


    st.write('Há ' + str(time_mask_after['time'].count()) + ' registros que violam os limites de horário final:')
    st.write(time_mask_after.sort_values(by=['time']))

else:
    st.write('Horários finais dentro do limite esperado')

#g = df[(df['flag'] == 1)]
#g['time'].count()


# In[13]:


#fora_horario = time_mask_before['time'].count() + time_mask_after['time'].count()
#fora_horario


# In[14]:


#verificações para Boleta
#time_before = df[(df['local'] == 'Boleta' ) & (df['time'] < time_open)]
#time_before.sort_values(by=['time']).sort_values(by=['time'])

#time_after = df[(df['local'] == 'Boleta' ) & (df['time'] > time_close)]
#time_after.sort_values(by=['time'])

#time_before['time'].count() + time_after['time'].count()


# # **Análises Relacionais**

# In[ ]:


st.header('Análises Relacionais')
#plt.figure(figsize=(16, 6))
#ax = sns.countplot(df['data'])
#plt.title("Operações por dia")
#plt.ylabel("Frequency", fontsize=14)
#plt.xlabel("")


# In[96]:



produto = np.array(df['produto'].unique())
sns.set_style('darkgrid')

sec_expander = st.expander(label='Visualizar lista de produtos')
with sec_expander:
    'Selecione um produto para visualizar a variação de preço ao longo do tempo.'
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
            plt.rc('xtick', labelsize=9)    # fontsize of the tick labels
            st.pyplot(fig)


#plt.figure(figsize=(20,10))
#sns.lineplot(data=df, x=df['data_completa'], y=df['preco'], hue=df['produto'], palette='flare')


# # **Análise Exploratória dos Dados**

# In[46]:


st.header('Data profiling')


# In[16]:


# descritivo dos dados
from pandas_profiling import ProfileReport
profile = ProfileReport(df, title=' ', config_file='volt_config.yaml')


# In[17]:


# visualização do relatório com pandas-profiling
#profile


# In[18]:


#exportar no formato html
#profile.to_file(output_file="dataframe_report.html")


# In[19]:


from streamlit_pandas_profiling import st_profile_report

#st.write(df)
st_profile_report(profile)


def get_download(df, arq):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode() 
    href = f'<a href="data:file/csv;base64,{b64}" download="'+arq+'.csv">Download</a>'
    return href

st.markdown(get_download(df, 'precos_bbce'), unsafe_allow_html=True)

