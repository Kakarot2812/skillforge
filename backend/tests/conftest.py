def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "qwen_integration: requires a running Ollama with the Qwen model (set QWEN_INTEGRATION=1)",
    )