"""The CLI exposes the documented commands."""

from typer.testing import CliRunner

from orionfold.cli import app

runner = CliRunner()


def test_help_lists_up_and_dev() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "up" in result.stdout
    assert "dev" in result.stdout
