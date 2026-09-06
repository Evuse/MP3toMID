from pathlib import Path


def test_required_monorepo_directories_exist() -> None:
    root = Path(__file__).parents[1]
    for directory in ("frontend", "backend", "audio-engine", "shared", "tests", "docker", "docs"):
        assert (root / directory).is_dir(), directory
