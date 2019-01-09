import service.config as config


def get_areas(cur, points, pointstable, distancewithin):
    tablecols = config.areas
    results = [{} for _ in range(len(points))]
    for table, (alias, columns) in tablecols.items():
        if distancewithin is not None and distancewithin > 0:
            cur.execute("""SELECT DISTINCT pts.id as ptsid, grid.{} FROM {} pts, {} grid 
                                        WHERE ST_DWithin(pts.geog, grid.geog, {}) 
                                        ORDER BY pts.id""".format(", grid.".join(columns), pointstable, table, distancewithin))
        else: # faster query
            cur.execute("""SELECT DISTINCT pts.id as ptsid, grid.{} FROM {} pts, {} grid 
                            WHERE ST_Intersects(grid.geom, pts.geom) 
                            ORDER BY pts.id""".format(", grid.".join(columns), pointstable, table))
        data = cur.fetchone()
        for idx in range(len(points)):
            results[idx][alias] = []
            while data and data[0] == idx:
                d = dict(zip(columns, data[1:]))
                results[idx][alias].append(d)
                data = cur.fetchone()
            if len(results[idx][alias]) == 0:
                del results[idx][alias]
    return results
        
        
def table_sql(req):
    def sqlval(x):
        if x is None:
            return 'NULL'
        elif isinstance(x, int):
            return str(x)
        return "'" + x.replace("'", "''") + "'"

    import psycopg2
    output = ["DELETE FROM obis.areas;"]
    with psycopg2.connect(config.connstring) as conn:
        with conn.cursor() as cur:
            for table, (alias, columns) in config.areas.items():
                cur.execute("SELECT distinct id::integer, name FROM {} ORDER BY id".format(table))
                data = cur.fetchone()
                output.append("-- Data from " + table)
                while data:
                    data = data + (alias,)
                    output.append("INSERT INTO obis.areas (id, name, type) VALUES ({});".format(", ".join(map(sqlval, data))))
                    data = cur.fetchone()

    return "\n".join(output) + "\n"
