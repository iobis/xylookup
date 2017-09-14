from falcon import testing
import pytest

import service.app

@pytest.fixture()
def client():
    return testing.TestClient(service.app.create())


def test_get_different_length_xy(client):
    result = client.simulate_get('/lookup', query_string = "x=3,4&y=2")
    assert result.status_code == 400
    assert "Invalid" in result.json["title"]
    assert "Length" in result.json["description"]


## THINGS TO TEST
# 1) query_string parameter validation
# 2) correct values areas
# 3) correct values landdistance
# 4) correct values rasters, check nodata works for all rasters
# 5) msgpack
# 6) POST doc works
# 7) POST doc parameter validation
