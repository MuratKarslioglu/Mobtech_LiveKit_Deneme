from app.providers.local_whisper_stt import _resolve_device


def test_resolve_device_explicit_cpu():
    assert _resolve_device("cpu") == ("cpu", "int8")


def test_resolve_device_explicit_cuda():
    assert _resolve_device("cuda") == ("cuda", "float16")


def test_resolve_device_auto_on_macos_falls_back_to_cpu(monkeypatch):
    monkeypatch.setattr(
        "app.providers.local_whisper_stt.platform.system", lambda: "Darwin"
    )
    assert _resolve_device("auto") == ("cpu", "int8")


def test_resolve_device_auto_on_linux_without_nvidia_smi_falls_back_to_cpu(monkeypatch):
    monkeypatch.setattr(
        "app.providers.local_whisper_stt.platform.system", lambda: "Linux"
    )
    monkeypatch.setattr(
        "app.providers.local_whisper_stt.shutil.which", lambda _name: None
    )
    assert _resolve_device("auto") == ("cpu", "int8")


def test_resolve_device_auto_on_linux_with_nvidia_smi_uses_cuda(monkeypatch):
    monkeypatch.setattr(
        "app.providers.local_whisper_stt.platform.system", lambda: "Linux"
    )
    monkeypatch.setattr(
        "app.providers.local_whisper_stt.shutil.which", lambda _name: "/usr/bin/nvidia-smi"
    )
    assert _resolve_device("auto") == ("cuda", "float16")
