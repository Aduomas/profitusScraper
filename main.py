# from IPython import display
import requests
from lxml import html
from lxml.etree import XPathEvalError
import pandas as pd
import sys
from configparser import ConfigParser

config = ConfigParser('config.ini')
email = config['login']['email']
password = config['login']['password']

df = pd.DataFrame()

url = 'https://profitus.lt/users/login'

resp = ''

with requests.session() as client:
  client.get(url)
  csrftoken = client.cookies['csrfToken']
  login_data = dict(email=email, password=password, _csrfToken=csrftoken, next='/')
  r = client.post(url, data=login_data, headers=dict(Referer=url))
  resp = client.get('https://www.profitus.lt/secondary-market') # ?page=5
  tree = html.fromstring(resp.text)
  next_url = 'https://profitus.lt' + tree.xpath('//a[@class="page-link-p fw-700"]')[0].values()[0]

  df = pd.read_html(resp.text)[0]
  try:
    while next_url:
      b = 2
      resp = client.get(next_url)
      print(resp.url)
      tree = html.fromstring(resp.text)
      next_url = 'https://profitus.lt' + tree.xpath('//a[@class="page-link-p fw-700"]')[b].values()[0]
      # df.merge(pd.read_html(resp.text)[0])
      df = pd.concat((df, pd.read_html(resp.text)[0]))
      if len(tree.xpath('//a[@class="page-link-p fw-700"]')) == 4:
        b = 2
      else:
        raise XPathEvalError('ok')
  except (XPathEvalError, IndexError):
      print('ok')
  print(df.columns)
df = df.drop(['Unnamed: 0', 'Unnamed: 9'], axis=1)

df['Projekto pavadinimas'] = df['Projekto pavadinimas'].map(lambda x: x.lstrip('Projekto pavadinimas:&nbsp '))
df['Reitingas'] = df['Reitingas'].map(lambda x: x.lstrip('Reitingas:&nbsp '))
df['Likęs terminas'] = df['Likęs terminas'].map(lambda x: x.lstrip('Likęs terminas:&nbsp ').rstrip('mėn.'))

df['Likęs terminas'] = df['Likęs terminas'].map(lambda x: x.split('/')[0]).astype(int)


df['Likusi suma'] = df['Likusi suma'].map(lambda x: x.lstrip('Likusi suma:&nbsp'))

df['Likusi suma'] = df['Likusi suma'].str.replace('€', '')
df['Likusi suma'] = df['Likusi suma'].str.replace(',', '').astype(float)

df['Palūkanų norma'] = df['Palūkanų norma'].map(lambda x: x.lstrip('Palūkanų norma:&nbsp'))

df['Palūkanų norma'] = df['Palūkanų norma'].str.replace('%', '').astype(float)


df['Statusas'] = df['Statusas'].map(lambda x: x.lstrip('Statusas:&nbsp'))

df['Statusas'] = df['Statusas'].str.replace('Aktyvus', '1')
df['Statusas'] = df['Statusas'].str.replace('Vėluoja', '2').astype(int)



df['Likusi gautina sumai'] = df['Likusi gautina sumai'].map(lambda x: x.lstrip('Likusi gautina suma:&nbsp '))

df['Likusi gautina sumai'] = df['Likusi gautina sumai'].str.replace('€', '')
df['Likusi gautina sumai'] = df['Likusi gautina sumai'].str.replace(',', '').astype(float)

df['Pardavimo kaina'] = df['Pardavimo kaina'].map(lambda x: x.lstrip('Pardavimo kaina:&nbsp '))

df['Pardavimo kaina'] = df['Pardavimo kaina'].str.replace('€', '')
df['Pardavimo kaina'] = df['Pardavimo kaina'].str.replace(',', '').astype(float)

df['profit%'] = (df['Likusi gautina sumai'] - df['Pardavimo kaina']) * 100 / df['Pardavimo kaina'] / (df['Likęs terminas']/12)
df.sort_values('profit%', ascending=False).head(10)
