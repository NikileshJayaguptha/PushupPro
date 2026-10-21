import time


def upload(client, workout, title="Test set"):
    with open(workout["path"], "rb") as f:
        r = client.post("/api/sessions", files={"file": ("workout.mp4", f, "video/mp4")}, data={"title": title})
    assert r.status_code == 201, r.text
    return r.json()


def wait_done(client, sid, timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        s = client.get(f"/api/sessions/{sid}").json()
        if s["status"] in ("done", "failed"):
            return s
        time.sleep(0.2)
    raise AssertionError("analysis did not finish")


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_full_flow(client, workout):
    created = upload(client, workout)
    assert created["status"] in ("queued", "processing")

    s = wait_done(client, created["id"])
    assert s["status"] == "done", s["error"]
    assert s["title"] == "Test set"
    assert s["rep_count"] == 4
    assert [("shallow_depth" in r["issues"]) for r in s["reps"]] == [False, False, True, False]
    assert "hip_sag" in s["reps"][3]["issues"]
    assert s["clean_reps"] == 2
    assert s["summary"]["issue_counts"] == {"shallow_depth": 1, "hip_sag": 1}

    trace = client.get(f"/api/sessions/{created['id']}/trace").json()
    assert len(trace["times"]) == workout["frames"]
    assert len(trace["keypoints"][0]) == 17
    assert trace["skeleton"]

    listed = client.get("/api/sessions").json()
    assert any(x["id"] == created["id"] for x in listed)


def test_video_range_requests(client, workout):
    sid = upload(client, workout)["id"]
    wait_done(client, sid)
    full = client.get(f"/api/sessions/{sid}/video")
    assert full.status_code == 200
    size = len(full.content)
    assert full.headers["accept-ranges"] == "bytes"

    part = client.get(f"/api/sessions/{sid}/video", headers={"Range": "bytes=10-99"})
    assert part.status_code == 206
    assert part.headers["content-range"] == f"bytes 10-99/{size}"
    assert part.content == full.content[10:100]

    bad = client.get(f"/api/sessions/{sid}/video", headers={"Range": f"bytes={size + 5}-"})
    assert bad.status_code == 416


def test_weekly_progress(client, workout):
    sid = upload(client, workout)["id"]
    wait_done(client, sid)
    p = client.get("/api/progress/weekly?weeks=4&tz=America/New_York").json()
    assert len(p["weeks"]) == 4
    this_week = p["weeks"][-1]
    assert this_week["sessions"] >= 1
    assert this_week["total_reps"] >= 4
    assert this_week["best_set"] == 4
    assert 0 < this_week["issue_rates"]["shallow_depth"] < 1
    assert p["totals"]["week_streak"] >= 1
    assert set(p["issue_labels"]) == {"shallow_depth", "incomplete_lockout", "hip_sag", "piking"}


def test_rename_reanalyze_delete(client, workout):
    sid = upload(client, workout)["id"]
    wait_done(client, sid)
    assert client.patch(f"/api/sessions/{sid}", json={"title": "Renamed"}).json()["title"] == "Renamed"

    assert client.post(f"/api/sessions/{sid}/reanalyze").status_code == 200
    assert wait_done(client, sid)["rep_count"] == 4

    assert client.delete(f"/api/sessions/{sid}").status_code == 204
    assert client.get(f"/api/sessions/{sid}").status_code == 404


def test_rejects_bad_uploads(client):
    r = client.post("/api/sessions", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert r.status_code == 415
    r = client.post("/api/sessions", files={"file": ("empty.mp4", b"", "video/mp4")})
    assert r.status_code == 400


def test_corrupt_video_fails_cleanly(client):
    r = client.post("/api/sessions", files={"file": ("broken.mp4", b"not a video at all" * 100, "video/mp4")})
    sid = r.json()["id"]
    s = wait_done(client, sid)
    assert s["status"] == "failed"
    assert s["error"]
