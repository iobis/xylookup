from falcon import testing
import falcon
import pytest
import msgpack
import service.app

# Terminal run: python -m pytest


@pytest.fixture()
def client():
    return testing.TestClient(service.app.create())


def simulate_msgpack_lookup(client, points):
    packed = msgpack.dumps(points)
    return client.simulate_post('/lookup', body=packed, headers={'Content-Type': falcon.MEDIA_MSGPACK})


def test_xy_different_length(client):
    result = client.simulate_get('/lookup', query_string = "x=3,4&y=2")
    assert result.status_code == 400
    assert "Invalid" in result.json["title"]
    assert "Length" in result.json["description"]


def test_xy_empty(client):
    result = client.simulate_get('/lookup', query_string="x=&y=")
    assert result.status_code == 400
    assert "Invalid" in result.json["title"]
    assert "Missing" in result.json["description"]


def test_xy_missing(client):
    result = client.simulate_get('/lookup')
    assert result.status_code == 400
    assert "Invalid" in result.json["title"]
    assert "Missing" in result.json["description"]


@pytest.mark.parametrize("x,y", [(0,91),(0,-91),(-181,0),(181,0)])
def test_xy_outside_world(client, x, y):
    result = client.simulate_get('/lookup', query_string='x={0}&y={1}'.format(x,y))
    assert result.status_code == 400
    assert "Invalid" in result.json["title"]
    assert "xmin" in result.json["description"]
    assert "ymin" in result.json["description"]


@pytest.mark.parametrize("x,y", [('a',0),(0,'b'),('0,0','1,b'),('1,b','0,0')])
def test_xy_not_numeric(client, x, y):
    result = client.simulate_get('/lookup', query_string='x={0}&y={1}'.format(x, y))
    assert result.status_code == 400
    assert "Invalid" in result.json["title"]
    assert "not numeric" in result.json["description"]


def test_post_json_invalid(client):
    result = client.simulate_post('/lookup', body='')
    assert result.status_code == 400
    assert "Invalid JSON" in result.json["title"]
    assert "JSON was incorrect" in result.json["description"]


def test_post_json_empty(client):
    result = client.simulate_post('/lookup', body='[]')
    assert result.status_code == 400
    assert "Invalid" in result.json["title"]
    assert "No coordinates provided" in result.json["description"]


def test_post_json_xy_outside_world(client):
    result = client.simulate_post('/lookup', body="""
    [[0, 1], [0, -1], [0, 0], [181, 0]]""")
    assert result.status_code == 400
    assert "Invalid" in result.json["title"]
    assert "xmin" in result.json["description"]
    assert "ymin" in result.json["description"]


def test_post_msgpack_invalid(client):
    result = client.simulate_post('/lookup', body='', headers={'Content-Type': 'application/msgpack'})
    assert result.status_code == 400
    assert "Invalid msgpack" in result.json["title"]
    assert "msgpack was incorrect" in result.json["description"]


def test_post_msgpack_empty(client):
    result = simulate_msgpack_lookup(client, [])
    assert result.status_code == 400
    assert "Invalid" in result.json["title"]
    assert "No coordinates provided" in result.json["description"]


def test_post_msgpack_xy_outside_world(client):
    result = simulate_msgpack_lookup(client, [[0, 1], [0, -1], [0, 0], [181, 0]])
    assert result.status_code == 400
    assert "Invalid" in result.json["title"]
    assert "xmin" in result.json["description"]
    assert "ymin" in result.json["description"]


def test_post_msgpack_xy_outside_world(client):
    result = simulate_msgpack_lookup(client, [['0', '1'], [0, -1], [0, 0], [181, 0]])
    assert result.status_code == 400
    assert "Invalid" in result.json["title"]
    assert "xmin" in result.json["description"]
    assert "ymin" in result.json["description"]


def check_1_values(data):
    data = data[0]
    assert len(data['areas']) > 0
    assert len(data['grids']) > 0
    assert 1680 < data['shoredistance'] < 1690
    grids = data['grids']
    assert grids['temperature (sea surface)'] == pytest.approx(12.475, 0.001)
    assert grids['salinity (sea surface)'] == pytest.approx(32.918, 0.001)
    assert grids['bathymetry'] == pytest.approx(5.2, 0.1)


def test_lookup_1_json_point_works(client):
    #x, y = 2.900152, 51.229310
    x, y = 2.890605926513672, 51.241779327392585
    result = client.simulate_get('/lookup', query_string='x={0}&y={1}'.format(x, y))
    assert result.status_code == 200
    data = result.json
    check_1_values(data)


def test_lookup_1_msgpack_point_works(client):
    result = simulate_msgpack_lookup(client, [[2.890605926513672, 51.241779327392585]])
    assert result.status_code == 200
    data = msgpack.loads(result.content)
    check_1_values(data)


def test_compare_results_r(client):
    import os
    print(os.getcwd())
    # TODO implement test
    pass
    #rdata = load_csv()


# def test_returns_correct_values(client):
#     points = [[0,0],['0','0']]
#     expected_final_area_names = [['North Atlantic', '']]
#     results = client.simulate_post('/lookup', body=json.dumps(points))
#     # TODO: continue TEST
#     """
#     [[{"layer": "final_grid5", "name": "South Atlantic", "country": null, "sp_id": "198", "base": "T", "type": "abnj"}, {"layer": "final_grid5", "name": "North Atlantic", "country": null, "sp_id": "157", "base": "T", "type": "abnj"}, {"layer": "final_grid5", "name": "ABNJ: all", "country": null, "sp_id": "abnj", "base": "F", "type": "abnj"}, "Salinity (sea surface)", "Temperature (sea surface)", "bathymetry", 572806.23312090512]]
#     """

# THINGS TO TEST
# 2) correct values areas
# 3) correct values landdistance
# 4) correct values rasters, check nodata works for all rasters
# 5) msgpack (receive)
# 7) POST doc parameter validation

