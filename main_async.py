# from IPython import display
import grequests
import requests
from lxml import html
import pandas as pd
import re

from configparser import ConfigParser

config = ConfigParser()
config.read('config.ini')
email = config['login']['email']
password = config['login']['password']

pd.set_option('display.max_rows', 100)

df = pd.DataFrame()

url = 'https://profitus.lt/users/login'

resp = ''

login_data = {}

def get_data():
  urls = []
  with requests.session() as client:
    client.get(url)
    csrftoken = client.cookies['csrfToken']
    login_data = dict(email=email, password=password, _csrfToken=csrftoken, next='/')
    r = client.post(url, data=login_data, headers=dict(Referer=url))
    resp = client.get('https://www.profitus.lt/secondary-market')
    tree = html.fromstring(resp.text)
    next_url = 'https://profitus.lt' + tree.xpath('//a[@class="page-link-p fw-700"]')[-1].values()[0]

    number_of_pages = int(re.search("\d+", next_url).group())

    for i in range(1, number_of_pages+1):
      urls.append(f'https://www.profitus.lt/secondary-market?page={i}')
      
    reqs = [grequests.get(link, headers=dict(Referer=url), session=client) for link in urls]
    resp = grequests.map(reqs)
    return resp

def parse_data(resp):
  global df
  for r in resp:
    print(r.url)
    df = pd.concat([df, pd.read_html(r.text)[0]])

  print('scraping is over!')

resp = get_data()
parse_data(resp)


df = df.drop(['Unnamed: 0', 'Unnamed: 9'], axis=1)

df['Projekto pavadinimas'] = df['Projekto pavadinimas'].map(lambda x: x.lstrip('Projekto pavadinimas:&nbsp '))
df['Reitingas'] = df['Reitingas'].map(lambda x: x.lstrip('Reitingas:&nbsp '))
df['Likęs terminas'] = df['Likęs terminas'].map(lambda x: x.lstrip('Likęs terminas:&nbsp ').rstrip('mėn.'))

df['Likęs terminas'] = df['Likęs terminas'].map(lambda x: x.split('/')[0]).astype(int) # 1 month and 29 days is considered as 1 month, we're calculating worst example possible. only those will be worth to buy


df['Likusi suma'] = df['Likusi suma'].map(lambda x: x.lstrip('Likusi suma:&nbsp'))

df['Likusi suma'] = df['Likusi suma'].str.replace('€', '')
df['Likusi suma'] = df['Likusi suma'].str.replace(',', '').astype(float)

df['Palūkanų norma'] = df['Palūkanų norma'].map(lambda x: x.lstrip('Palūkanų norma:&nbsp'))

df['Palūkanų norma'] = df['Palūkanų norma'].str.replace('%', '').astype(float)


df['Statusas'] = df['Statusas'].map(lambda x: x.lstrip('Statusas:&nbsp'))


# df['Statusas'] = df['Statusas'].str.replace('Aktyvus', '1')
# df['Statusas'] = df['Statusas'].str.replace('Vėluoja', '2').astype(int)



df['Likusi gautina sumai'] = df['Likusi gautina sumai'].map(lambda x: x.lstrip('Likusi gautina suma:&nbsp '))

df['Likusi gautina sumai'] = df['Likusi gautina sumai'].str.replace('€', '')
df['Likusi gautina sumai'] = df['Likusi gautina sumai'].str.replace(',', '').astype(float)

df['Pardavimo kaina'] = df['Pardavimo kaina'].map(lambda x: x.lstrip('Pardavimo kaina:&nbsp '))

df['Pardavimo kaina'] = df['Pardavimo kaina'].str.replace('€', '')
df['Pardavimo kaina'] = df['Pardavimo kaina'].str.replace(',', '').astype(float)

import numpy as np
df[df['Likęs terminas'] < 1] = 1
df['Realios palūkanos'] = (np.power(df['Likusi gautina sumai'] / df['Pardavimo kaina'], 1/((df['Likęs terminas'] + 1)/12)) - 1 ) * 100
df['diff'] = (df['Realios palūkanos'] - df['Palūkanų norma'])

print(df[(df['Palūkanų norma'] - df['Realios palūkanos']) < 0]) # basically we're trying to find projects that have largest interest rate, than
df.sort_values('Realios palūkanos', ascending=False).head(100)


# sent_mail = df[(df['Palūkanų norma'] - df['Realios palūkanos']) < 0]
sent_mail = df[df['diff'] > 0]


import smtplib, ssl
import io
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

port = 465
password = config['login']['from_password']

str_io = io.StringIO()
sent_mail.to_html(buf=str_io, classes='table table-striped')
html_str = str_io.getvalue()
context = ssl.create_default_context()

msg = MIMEMultipart('alternative')
msg['Subject'] = 'Profitus daily'
msg['From'] = config['login']['from_email']
from datetime import datetime
text = f"Hi this is {datetime.now().strftime('%m-%d')} report"
part1 = MIMEText(text, 'plain')
part2 = MIMEText(html_str, 'html')

msg.attach(part1)
msg.attach(part2)

with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
  server.login(config['login']['from_email'], password)
  server.sendmail(config['login']['from_email'], "XXX", msg.as_string())
  server.sendmail(config['login']['from_email'], "XXX", msg.as_string())
  