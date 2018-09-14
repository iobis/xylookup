import os
datadir = os.path.expanduser('~/Dropbox (IPOfI)/xylookup/datadir')
connstring = "dbname=xylookup user=postgres port=5432 password=postgres"
areas = {'final_grid5': ('obis', ['id', 'name', 'country', 'type', 'base'])}