from pathlib import Path

import yaml

ROOT = Path(__file__).parents[2]


def test_render_blueprint_uses_backend_docker_and_pages_cors() -> None:
    blueprint = yaml.safe_load((ROOT / "render.yaml").read_text())
    service = blueprint["services"][0]
    assert service["runtime"] == "docker"
    assert service["dockerfilePath"] == "./backend/Dockerfile"
    assert service["dockerContext"] == "./backend"
    environment = {item["key"]: item["value"] for item in service["envVars"]}
    assert environment["CORS_ORIGINS"] == "https://ardn87jj.github.io"
    assert environment["MAX_CONCURRENT_JOBS"] == 1


def test_pages_workflow_builds_repository_subpath_with_api_variable() -> None:
    workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text()
    assert "VITE_BASE_PATH: /Musicto432/" in workflow
    assert "VITE_API_URL: ${{ vars.VITE_API_URL }}" in workflow
    assert "actions/deploy-pages@v4" in workflow


def test_frontend_has_no_root_absolute_brand_path() -> None:
    app = (ROOT / "frontend" / "src" / "App.tsx").read_text()
    assert 'src="/brand/' not in app
    assert "import.meta.env.BASE_URL" in app
