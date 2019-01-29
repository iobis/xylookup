import os

datadir = os.path.expanduser('/data/xylookup/datadir')
dataprepdir = os.path.expanduser('/data/xylookup/dataprep')
connstring = "dbname=xylookup user=postgres port=5432 password=postgres"

areas = {
    "final_fixed_grid5": ("obis", ["id", "name"]),
    "abnj_grid5": ("abnj", ["id", "name"]), 
    "ebsa_grid5": ("ebsa", ["id", "name"]),
    "mwhs_grid5": ("mwhs", ["id", "name"]),
    "lme_grid5": ("lme", ["id", "name"]),
    "iho_grid5": ("iho", ["id", "name"])
}
