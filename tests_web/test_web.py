from fastapi.testclient import TestClient
from web.server import app

client = TestClient(app)

def test_read_write_settings():
    response = client.post("/api/settings/test", params={"value": "123"})
    assert response.status_code == 200
    data = response.json()
    assert data["value"] == "123"


def test_transcribe(monkeypatch):
    class DummyModel:
        def transcribe(self, path):
            return {"text": "hi"}

    monkeypatch.setattr("whisper.load_model", lambda name: DummyModel())
    resp = client.post("/api/transcribe", files={"file": ("test.wav", b"data")})
    assert resp.status_code == 200
    assert resp.json()["text"] == "hi"


def test_tts(monkeypatch):
    class DummyTTS:
        def save(self, path):
            with open(path, "wb") as f:
                f.write(b"a")

    monkeypatch.setattr("gtts.gTTS", lambda text, lang="en": DummyTTS())
    resp = client.post("/api/tts", data={"text": "hello"})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "audio/mpeg"


def test_chat(monkeypatch):
    class DummyChoice:
        message = type("obj", (), {"content": "world"})()

    class DummyComp:
        choices = [DummyChoice]

    class DummyClient:
        class chat:
            class completions:
                @staticmethod
                def create(model, messages):
                    return DummyComp()

    monkeypatch.setattr("openai.OpenAI", lambda: DummyClient())
    resp = client.post("/api/chat", data={"message": "hello"})
    assert resp.status_code == 200
    assert resp.json()["text"] == "world"


def test_models():
    resp = client.get("/api/models")
    assert resp.status_code == 200
    assert "models" in resp.json()

    response = client.get("/api/settings/test")
    assert response.status_code == 200
    data = response.json()
    assert data["value"] == "123"
