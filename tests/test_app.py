from falcon import testing
import falcon
import pytest
import umsgpack as msgpack
import json
import csv
import service.app as app
import service.config as config

# Terminal run: python -m pytest


@pytest.fixture()
def client():
    return testing.TestClient(app.create())


def simulate_msgpack_lookup(client, points):
    packed = msgpack.dumps({'points': points})
    return client.simulate_post('/lookup', body=packed, headers={'Content-Type': falcon.MEDIA_MSGPACK})


def test_xy_different_length(client):
    print('test_xy_different_length')
    result = client.simulate_get('/lookup', query_string = "x=3,4&y=2")
    assert result.status_code == 400
    assert "Invalid" in result.json["title"]
    assert "Length" in result.json["description"]


def test_xy_empty(client):
    print('test_xy_empty')
    result = client.simulate_get('/lookup', query_string="x=&y=")
    assert result.status_code == 400
    assert "Invalid" in result.json["title"]
    assert "Missing" in result.json["description"]


def test_xy_missing(client):
    print('test_xy_missing')
    result = client.simulate_get('/lookup')
    assert result.status_code == 400
    assert "Invalid" in result.json["title"]
    assert "Missing" in result.json["description"]


@pytest.mark.parametrize("x,y", [(0,91),(0,-91),(-181,0),(181,0)])
def test_xy_outside_world(client, x, y):
    print('test_xy_outside_world')
    result = client.simulate_get('/lookup', query_string='x={0}&y={1}'.format(x,y))
    assert result.status_code == 400
    assert "Invalid" in result.json["title"]
    assert "xmin" in result.json["description"]
    assert "ymin" in result.json["description"]


@pytest.mark.parametrize("x,y", [('a',0),(0,'b'),('0,0','1,b'),('1,b','0,0')])
def test_xy_not_numeric(client, x, y):
    print('test_xy_not_numeric')
    result = client.simulate_get('/lookup', query_string='x={0}&y={1}'.format(x, y))
    assert result.status_code == 400
    assert "Invalid" in result.json["title"]
    assert "not numeric" in result.json["description"]


def test_post_json_invalid(client):
    print('test_post_json_invalid')
    result = client.simulate_post('/lookup', body='')
    assert result.status_code == 400
    assert "Invalid JSON" in result.json["title"]
    assert "JSON was incorrect" in result.json["description"]


def test_post_json_not_dict(client):
    print('test_post_json_not_dict')
    result = client.simulate_post('/lookup', body='[]')
    assert result.status_code == 400
    assert "Invalid" in result.json["title"]
    assert "dictionary" in result.json["description"]


def test_post_json_empty(client):
    print('test_post_json_empty')
    result = client.simulate_post('/lookup', body='{"points":[]}')
    assert result.status_code == 400
    assert "Invalid" in result.json["title"]
    assert "No points provided" in result.json["description"]


def test_post_json_xy_outside_world(client):
    print('test_post_json_xy_outside_world')
    result = client.simulate_post('/lookup', body="""{"points":
    [[0, 1], [0, -1], [0, 0], [181, 0]]}""")
    assert result.status_code == 400
    assert "Invalid" in result.json["title"]
    assert "xmin" in result.json["description"]
    assert "ymin" in result.json["description"]


def test_post_msgpack_invalid(client):
    print('test_post_msgpack_invalid')
    result = client.simulate_post('/lookup', body='', headers={'Content-Type': 'application/msgpack'})
    assert result.status_code == 400
    assert "Invalid msgpack" in result.json["title"]
    assert "msgpack was incorrect" in result.json["description"]


def test_post_msgpack_not_dict(client):
    print('test_post_msgpack_not_dict')
    packed = msgpack.dumps("not a dictionary")
    result = client.simulate_post('/lookup', body=packed, headers={'Content-Type': falcon.MEDIA_MSGPACK})
    assert result.status_code == 400
    assert "Invalid" in result.json["title"]
    assert "dictionary" in result.json["description"]


def test_post_msgpack_empty(client):
    print('test_post_msgpack_empty')
    result = simulate_msgpack_lookup(client, points=[])
    assert result.status_code == 400
    assert "Invalid" in result.json["title"]
    assert "No points provided" in result.json["description"]


def test_post_msgpack_xy_outside_world(client):
    print('test_post_msgpack_xy_outside_world')
    result = simulate_msgpack_lookup(client, points=[[0, 1], [0, -1], [0, 0], [181, 0]])
    assert result.status_code == 400
    assert "Invalid" in result.json["title"]
    assert "xmin" in result.json["description"]
    assert "ymin" in result.json["description"]


def test_post_msgpack_xy_outside_world(client):
    print('test_post_msgpack_xy_outside_world')
    result = simulate_msgpack_lookup(client, points=[['0', '1'], [0, -1], [0, 0], [181, 0]])
    assert result.status_code == 400
    assert "Invalid" in result.json["title"]
    assert "xmin" in result.json["description"]
    assert "ymin" in result.json["description"]


def check_1_values(data):
    data = data[0]
    assert len(data['areas']) > 0 and len(data['areas'][list(config.areas.keys())[0]]) > 0
    assert len(data['grids']) > 0
    assert 1680 < data['shoredistance'] < 1690
    grids = data['grids']
    assert grids['temperature (sea surface)'] == pytest.approx(12.475, 0.001)
    assert grids['salinity (sea surface)'] == pytest.approx(32.918, 0.001)
    assert grids['bathymetry'] == pytest.approx(5.2, 0.1)


def test_lookup_1_json_point_works(client):
    print('test_lookup_1_json_point_works')
    x, y = 2.890605926513672, 51.241779327392585
    result = client.simulate_get('/lookup', query_string='x={0}&y={1}'.format(x, y))
    assert result.status_code == 200
    print(result.content)
    print(result.json)
    data = result.json
    check_1_values(data)


def test_lookup_1_msgpack_point_works(client):
    print('test_lookup_1_msgpack_point_works')
    result = simulate_msgpack_lookup(client, [[2.890605926513672, 51.241779327392585]])
    assert result.status_code == 200
    data = msgpack.loads(result.content)
    check_1_values(data)


def test_compare_results_r(client):
    print('test_compare_results_r')
    def assert_value(d, key, expectedv, tolerance):
        if key in d:
            assert grids[key] == pytest.approx(float(expectedv), tolerance), "wrong result point {0} {1}".format(i, points[i])
        else:
            assert expectedv == 'NA', "wrong result point {0} {1}".format(i, points[i])
    points = [] # x/y
    pointvalues = [] # sst/sss/bathymetry
    with open("./tests/r_testlookup.csv") as csvfile:
        reader = csv.reader(csvfile, delimiter=",")
        for i, row in enumerate(reader):
            if i > 0:
                points.append(row[0:2])
                pointvalues.append(row[2:5])
    results = simulate_msgpack_lookup(client, points)
    data = msgpack.loads(results.content)
    for i, actual in enumerate(data):
        expected = pointvalues[i]
        grids = actual['grids']
        assert_value(grids, 'temperature (sea surface)', expected[0], 0.001)
        assert_value(grids, 'salinity (sea surface)', expected[1], 0.001)
        assert_value(grids, 'bathymetry', expected[2], 0.1)


@pytest.mark.parametrize("extra_params", [{}, {'areas': False}, {'grids': False}, {'shoredistance': False},
                                          {'areas': False, 'grids': False, 'shoredistance': False}])
def test_get_results_filtering(client, extra_params):
    print('test_get_results_filtering')
    x, y = 2.890605926513672, 51.241779327392585
    extra = '&'.join([k + '=' + str(v).lower() for k,v in extra_params.items()])
    if extra:
        extra = '&' + extra
    result = client.simulate_get('/lookup', query_string='x={0}&y={1}'.format(x, y) + extra)
    assert result.status_code == 200
    data = result.json[0]
    assert extra_params.get('areas', True) == ('areas' in data)
    assert extra_params.get('grids', True) == ('grids' in data)
    assert extra_params.get('shoredistance', True) == ('shoredistance' in data)


@pytest.mark.parametrize("extra_params", [{}, {'areas': False}, {'grids': False}, {'shoredistance': False},
                                          {'areas': False, 'grids': False, 'shoredistance': False}])
def test_post_json_results_filtering(client, extra_params):
    print('test_post_json_results_filtering')
    d = {'points': [[2.890605926513672, 51.241779327392585]]}
    d.update(extra_params)
    body = json.dumps(d)
    result = client.simulate_post('/lookup', body=body)
    assert result.status_code == 200
    data = result.json[0]
    assert extra_params.get('areas', True) == ('areas' in data)
    assert extra_params.get('grids', True) == ('grids' in data)
    assert extra_params.get('shoredistance', True) == ('shoredistance' in data)


@pytest.mark.parametrize("extra_params", [{}, {'areas': False}, {'grids': False}, {'shoredistance': False},
                                          {'areas': False, 'grids': False, 'shoredistance': False}])
def test_post_msgpack_results_filtering(client, extra_params):
    print('test_post_msgpack_results_filtering')
    d = {'points': [[2.890605926513672, 51.241779327392585]]}
    d.update(extra_params)
    packed = msgpack.dumps(d)
    results = client.simulate_post('/lookup', body=packed, headers={'Content-Type': falcon.MEDIA_MSGPACK})
    data = msgpack.loads(results.content)[0]
    assert extra_params.get('areas', True) == ('areas' in data)
    assert extra_params.get('grids', True) == ('grids' in data)
    assert extra_params.get('shoredistance', True) == ('shoredistance' in data)
