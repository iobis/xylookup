# xylookup
Webservice for looking up environmental and societal spatial information based on coordinates.

## API

Documentation

<https://iobis.github.io/xylookup/>

Get all data for a point as json

<http://api.iobis.org/xylookup?x=2.90&y=51.2>

Get all data for multiple points as json

<http://api.iobis.org/xylookup?x=2.90,2.1&y=51.2,51.1>

Filtering the results can be done by excluding the different categories(`areas`, `shoredistance`, `grids`) e.g.
to return results without the distance to the shoreline:

<http://api.iobis.org/xylookup?x=2.90&y=51.2&shoredistance=0>

Note that msgpack data can also be used for sending/receiving data.

## In R: obistools 

```R
devtools::install_github('iobis/obistools')

library(obistools)

?lookup_xy


xydata <- lookup_xy(abra, shoredistance = TRUE, grids = TRUE, areas = TRUE)
head(xydata)
```

```
shoredistance sstemperature sssalinity bathymetry                                                                                                   final_grid5
1            30      10.28631   34.76271       -4.0 United Kingdom, United Kingdom, F, T, eez, eez, United Kingdom: all, United Kingdom, United Kingdom: all, 221
2          1080      10.33242   34.90622       61.4 United Kingdom, United Kingdom, T, F, eez, eez, United Kingdom, United Kingdom: all, 221, United Kingdom: all
3          1184      10.72199   34.88896      122.2 United Kingdom, United Kingdom, T, F, eez, eez, United Kingdom, United Kingdom: all, 221, United Kingdom: all
4           290      10.79197   34.29342       20.6 United Kingdom, United Kingdom, F, T, eez, eez, United Kingdom: all, United Kingdom, United Kingdom: all, 221
5           259      10.72199   34.88896       51.0 United Kingdom, United Kingdom, F, T, eez, eez, United Kingdom: all, United Kingdom, United Kingdom: all, 221
6           506      10.77101   34.30700       32.4 United Kingdom, United Kingdom, F, T, eez, eez, United Kingdom: all, United Kingdom, United Kingdom: all, 221
```

## In python: pyxylookup

Documentation: <http://pyxylookup.readthedocs.io/en/latest/>  
Installation:

```bash
pip install git+https://github.com/iobis/pyxylookup.git#egg=pyxylookup
```

```python
import pyxylookup as xy

xy.lookup([[120,0], [-170,1]])
```

## Dependencies

- PostgreSQL and PostGIS (currently tested on 9.6 and 9.4)
- Python 2.7 or 3.6 with
    - falcon
    - numpy
    - msgpack
    - psycopg2
    - gunicorn (webserver)
    - gdal (for the datapreparation scripts, not for the service itself)
- nginx

## Deployment

- Install postgresql
    - Load the needed areas tables into PostgreSQL
        - Currently only `final_grid5` (see below)
- Install nginx
- Install python
- Copy the source code from the service directory
- Copy the datadir
- Start gunicorn 
    - `gunicorn --reload app:api`
    - Preferably make sure that gunicorn restarts when the service restarts
- Configure nginx so that it proxies all calls to gunicorn
- Update service/config.py, set the datadir, PostgreSQL connection string and if needed the available areas.

### Important commands

Manually running tests

    python -m pytest
    
Starting the gunicorn service on the server

    sudo systemctl start xylookup_service 

## Data pre-processing

### final_grid5

Starting from the final.shp shapefile, perform the following steps:

    D:\a\prog\PostgreSQL\9.6\bin\shp2pgsql -I -s 4326 final.shp final postgres > final.sql
    psql -d xylookup -U postgres -p 5433 -f final.sql
    
    QGIS => Vector => research tools => Vector grid
    xmin -180.000001 ymin -90.000001
    xmax 180.000001 ymax 90.000001
    
    X: 5,000000030
    Output grid as polygons
    D:/a/projects/iobis/xylookup/vector/data/gridpoly_5.shp
    
    QGIS => Vector => Geoprocessing => Intersect
    final
    gridpoly_5
    D:/a/projects/iobis/xylookup/vector/data/final_grid5.shp
    
    D:\a\prog\PostgreSQL\9.6\bin\shp2pgsql -I -s 4326 final_grid5.shp final_grid5 postgres > final_grid5.sql
    psql -d xylookup -U postgres -p 5433 -f final_grid5.sql


    # in sql replace the id column values to generate area ids
    update final_grid5 as f set id = t.id from (select row_number() over (order by name, country, type, base) as id, sp_id, name, country, type, base 
    from final_grid5 group by sp_id, name, country, type, base order by name, country, type, base) t where f.sp_id = t.sp_id;

    # areas table then becomes
    create table areas as select distinct id::integer, sp_id, name, country, type, base from final_grid5 order by id


### Shore distance

All data used was downloaded from [Open Street Map](http://openstreetmapdata.com/data/coast).

In order to calculate the shoredistance we need two parts:

1. water polygons in the database which are used to test whether points are on land
    - download [water polygons](http://openstreetmapdata.com/data/water-polygons)
    - simplify
        - `ogr2ogr water_polygons0_00005.shp water_polygons.shp -simplify 0.00005`
    - upload to PostgreSQL
        - `shp2pgsql -s 4326 water_polygons0_00005 public.water_polygons0_00005 > water.sql`
        - `psql -d xylookup -U postgres -p 5433 -f water.sql`
2. coastlines as geojson that are loaded in the python service for calculating the shoredistance
    - download [coastlines](http://openstreetmapdata.com/data/coastlines)
    - import coastline-split-4326 as table coastlines in database xylookup using the QGIS DBManager because the dbf file gives errors with shp2pgsql

Then execute the following sql code in PostgreSQL:
  
    CREATE OR REPLACE FUNCTION simplifyutm(geom geometry, tolerance float, max_segment_length float)
       RETURNS geometry AS
    $BODY$
    DECLARE
         bestUTM integer;
         geomCenter geometry;
         geomUTM geometry;
         geomBack geometry;
    BEGIN
         geomCenter:= ST_centroid(geom);
         bestUTM:= floor((ST_X(geomCenter)+180)/6)+1;
         IF (ST_Y(geomCenter))>0 THEN
            bestUTM:= bestUTM+32600;
         ELSE
            bestUTM:= bestUTM+32700;
         END IF;
         geomUTM:= ST_Transform(geom,bestUTM);
         geomUTM:= ST_SimplifyPreserveTopology(geomUTM, tolerance);
         geomUTM:= ST_Segmentize(geomUTM, max_segment_length);
         geomBack:= ST_Transform(ST_setsrid(geomUTM, bestUTM),4326); -- set_srid as it is sometimes lost for some features ...
         RETURN geomBack;
    END
    $BODY$
       LANGUAGE plpgsql STABLE STRICT;

    SELECT AddGeometryColumn('coastlines', 'geom_simple50', 4326, 'LINESTRING', 2);
    UPDATE coastlines SET geom_simple50 = simplifyutm(geom, 50, 500);
    COPY (SELECT st_asgeojson(geom_simple50) FROM coastlines) TO '<datadir>/coastlines50.jsonlines';

### Rasters

Run dataprep/rasters.py, it prepares both the data and metadata needed. Data is prepared by storing them as uncompressed binary numpy array files which are later on read by using memorymapped files.

Some input source data will have to be downloaded manually such as the EMODnet and GEBCO bathymetry.

## Roadmap

Add support for looking up data based on time and depth.  
Document the api using Swagger.  

# xylookup OpenAPI Specification
[![Build Status](https://travis-ci.org/iobis/xylookup.svg?branch=master)](https://travis-ci.org/iobis/xylookup)

## Links

- Documentation(ReDoc): https://iobis.github.io/xylookup/
- SwaggerUI: https://iobis.github.io/xylookup/swagger-ui/
- Look full spec:
    + JSON https://iobis.github.io/xylookup/swagger.json
    + YAML https://iobis.github.io/xylookup/swagger.yaml
- Preview spec version for branch `[branch]`: https://iobis.github.io/xylookup/preview/[branch]

**Warning:** All above links are updated only after Travis CI finishes deployment

## Working on specification
### Install

1. Install [Node JS](https://nodejs.org/)
2. Clone repo and `cd`
    + Run `npm install`

### Usage

1. Run `npm start`
2. Checkout console output to see where local server is started. You can use all [links](#links) (except `preview`) by replacing https://iobis.github.io/xylookup/ with url from the message: `Server started <url>`
3. Make changes using your favorite editor or `swagger-editor` (look for URL in console output)
4. All changes are immediately propagated to your local server, moreover all documentation pages will be automagically refreshed in a browser after each change
**TIP:** you can open `swagger-editor`, documentation and `swagger-ui` in parallel
5. Once you finish with the changes you can run tests using: `npm test`
6. Share you changes with the rest of the world by pushing to GitHub

## Data references and acknowledgements

Claus S., N. De Hauwere, B. Vanhoorne, F. Souza Dias, P. Oset García, F. Hernandez, and J. Mees (Flanders Marine Institute) (2017). MarineRegions.org.  

The GEBCO_2014 Grid, version 20150318, http://www.gebco.net.  

EMODnet Bathymetry Consortium (2016): EMODnet Digital Bathymetry (DTM). http://doi.org/10.12770/c7b53704-999d-4721-b1a3-04ec60c87238.  

Tyberghein L, Verbruggen H, Pauly K, Troupin C, Mineur F, De Clerck O (2012) Bio-ORACLE: A global environmental dataset for marine species distribution modelling. Global Ecology and Biogeography, 21, 272–281.  

Map data copyrighted OpenStreetMap contributors and available from https://www.openstreetmap.org.  
    