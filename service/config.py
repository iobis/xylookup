import os

datadir = os.path.expanduser('~/Desktop/dev/datadir')
dataprepdir = os.path.expanduser('~/Desktop/dev/dataprep')
connstring = "dbname=xylookup user=postgres port=5432 password=postgres"

areas = {
    "final_grid5": ("obis", ["id", "name", "type"]),
    "ebsa_grid5": ("ebsa", ["id", "name"]),
    "mwhs_grid5": ("mwhs", ["id", "name"]),
    "lme_grid5": ("lme", ["id", "name"]),
    "iho_grid5": ("iho", ["id", "name"])
}