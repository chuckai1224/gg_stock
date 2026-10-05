import pandas as pd
df = pd.read_csv('data/stock_data/2330.csv')
df['ym'] = df['date'].str[:7]
print(df.groupby('ym').size())
