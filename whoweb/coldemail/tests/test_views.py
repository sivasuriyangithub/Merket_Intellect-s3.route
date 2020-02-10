import pytest


pytestmark = pytest.mark.django_db

TEST_QUERY = {
    "user_id": None,
    "filters": {"limit": 10, "skip": 0, "required": [], "desired": [], "profiles": [],},
    "defer": [],
    "with_invites": False,
    "contact_filters": [],
    "export": {"webhooks": [], "title": "", "metadata": {}, "format": "nested",},
}


def test_create_campaignmessage(su_client):
    resp = su_client.post(
        "/ww/api/campaign_messages/",
        {
            "title": "test",
            "subject": "Click here",
            "html_content": "<h1>Yo</h1>",
            "plain_content": "Yo!",
            "editor": "client",
        },
        format="json",
    )
    print(resp.content)
    assert resp.status_code == 201
    assert resp.json()["url"].startswith("http://testserver/ww/api/campaign_messages/")
    assert resp.json()["title"] == "test"

    listed = su_client.get("/ww/api/campaign_messages/", format="json",)
    assert len(listed.json()["results"]) == 1


def test_update_campaignmessage(su_client):
    resp = su_client.post(
        "/ww/api/campaign_messages/",
        {
            "title": "test",
            "subject": "Click here",
            "html_content": "<h1>Yo</h1>",
            "plain_content": "Yo!",
            "editor": "client",
        },
        format="json",
    )
    url = resp.json()["url"]
    assert resp.status_code == 201
    assert resp.json()["title"] == "test"

    update = su_client.patch(url, {"title": "new title"}, format="json",)
    assert update.json()["title"] == "new title"
    assert update.json()["editor"] == resp.json()["editor"] == "client"


def test_delete_campaignmessage(su_client):
    resp = su_client.post(
        "/ww/api/campaign_messages/",
        {
            "title": "test",
            "subject": "Click here",
            "html_content": "<h1>Yo</h1>",
            "plain_content": "Yo!",
            "editor": "client",
        },
        format="json",
    )
    url = resp.json()["url"]
    delete = su_client.delete(url, format="json",)
    assert delete.status_code == 204

    listed = su_client.get("/ww/api/campaign_messages/", format="json",)
    assert len(listed.json()["results"]) == 0


def test_create_campaignlist(su_client):
    resp = su_client.post(
        "/ww/api/campaign_lists/",
        {"query": TEST_QUERY, "name": "list name", "origin": "1",},
        format="json",
    )
    print(resp.content)
    assert resp.status_code == 201
    assert resp.json()["url"].startswith("http://testserver/ww/api/campaign_lists/")
    assert resp.json()["name"] == "list name"

    listed = su_client.get("/ww/api/campaign_lists/", format="json",)
    assert len(listed.json()["results"]) == 1


def test_update_campaignlist(su_client):
    resp = su_client.post(
        "/ww/api/campaign_lists/",
        {"query": TEST_QUERY, "name": "list name", "origin": "1",},
        format="json",
    )
    url = resp.json()["url"]
    assert resp.status_code == 201
    assert resp.json()["name"] == "list name"

    update = su_client.patch(url, {"name": "new name"}, format="json",)
    assert update.json()["name"] == "new name"


def test_delete_campaignlist(su_client):
    resp = su_client.post(
        "/ww/api/campaign_lists/",
        {"query": TEST_QUERY, "name": "list name", "origin": "1",},
        format="json",
    )
    url = resp.json()["url"]
    delete = su_client.delete(url, format="json",)
    assert delete.status_code == 204

    listed = su_client.get("/ww/api/campaign_lists/", format="json",)
    assert len(listed.json()["results"]) == 0
