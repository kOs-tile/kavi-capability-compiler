from labs.plugin_doctor.scorecard import render_scorecard, write_scorecard


def test_scorecard_escapes_untrusted_content_and_rejects_unsafe_links(tmp_path):
    report = {
        "source": {
            "kind": "github",
            "repository": "https://github.com/acme/demo",
            "ref": "main",
        },
        "package": {
            "state": "BLOCKED",
            "score": 42,
            "summary": {"findings": 1, "blockers": 1},
            "findings": [
                {
                    "code": "PD-XSS",
                    "severity": "high",
                    "message": "<script>alert('x')</script>",
                    "remediation": "<img src=x onerror=alert(1)>",
                    "source_url": "javascript:alert(1)",
                }
            ],
        },
    }

    rendered = render_scorecard(report, title="<Plugin>")

    assert "<script>" not in rendered
    assert "<img src=x" not in rendered
    assert "javascript:alert(1)" not in rendered
    assert "&lt;script&gt;" in rendered
    assert "&lt;Plugin&gt;" in rendered

    path = write_scorecard(report, tmp_path / "report.html", title="Fixture")
    assert path.exists()
    assert "BLOCKED" in path.read_text(encoding="utf-8")


def test_scorecard_renders_official_https_source_link():
    report = {
        "state": "FIX",
        "score": 80,
        "summary": {"findings": 1},
        "findings": [
            {
                "code": "PD-OAI",
                "severity": "medium",
                "message": "Fix metadata.",
                "source_url": "https://developers.openai.com/plugins/plugin-guidelines",
            }
        ],
    }

    rendered = render_scorecard(report)

    assert "official source" in rendered
    assert "https://developers.openai.com/plugins/plugin-guidelines" in rendered
