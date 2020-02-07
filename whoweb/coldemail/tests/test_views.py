import pytest


pytestmark = pytest.mark.django_db


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
    delete = su_client.patch(url, {"title": "new title"}, format="json",)
    assert delete.status_code == 200

    listed = su_client.get("/ww/api/campaign_messages/", format="json",)
    assert len(listed.json()["results"]) == 0


def test_create_campaignlist(su_client):
    resp = su_client.post(
        "/ww/api/campaign_lists/",
        {
            "title": "test",
            "subject": "Click here",
            "html_content": "<h1>Yo</h1>",
            "plain_content": "Yo!",
            "editor": "client",
        },
        format="json",
    )
    assert resp.status_code == 201
    assert resp.json()["url"].startswith("http://testserver/ww/api/campaign_lists/")
    assert resp.json()["title"] == "test"

    listed = su_client.get("/ww/api/campaign_lists/", format="json",)
    assert len(listed.json()["results"]) == 1


def test_update_campaignlist(su_client):
    resp = su_client.post(
        "/ww/api/campaign_lists/",
        {
            "query": "test",
            "name": "list name",
            "origin": "1",
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


def test_delete_campaignlist(su_client):
    resp = su_client.post(
        "/ww/api/campaign_lists/",
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
    delete = su_client.patch(url, {"title": "new title"}, format="json",)
    assert delete.status_code == 200

    listed = su_client.get("/ww/api/campaign_lists/", format="json",)
    assert len(listed.json()["results"]) == 0
