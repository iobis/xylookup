from falcon import testing
import pytest

import service.app

# Terminal run: python -m pytest


@pytest.fixture()
def client():
    return testing.TestClient(service.app.create())


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

# THINGS TO TEST
# 1) query_string parameter validation
# 2) correct values areas
# 3) correct values landdistance
# 4) correct values rasters, check nodata works for all rasters
# 5) msgpack
# 6) POST doc works
# 7) POST doc parameter validation
