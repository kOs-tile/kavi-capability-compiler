from labs.plugin_doctor.evals import InvocationCase, run_invocation_evals


TOOLS = [
    {
        "name": "search_docs",
        "description": "Search product documentation for setup, API, and integration guidance.",
    },
    {
        "name": "delete_document",
        "description": "Delete one stored document permanently by document identifier.",
    },
]


def test_lexical_baseline_handles_positive_and_negative_activation():
    report = run_invocation_evals(
        TOOLS,
        [
            InvocationCase(
                case_id="search-positive",
                prompt="Search the docs for OAuth setup guidance",
                expected_tools=("search_docs",),
                forbidden_tools=("delete_document",),
            ),
            InvocationCase(
                case_id="delete-positive",
                prompt="Delete this document permanently",
                expected_tools=("delete_document",),
                forbidden_tools=("search_docs",),
            ),
            InvocationCase(
                case_id="unrelated-negative",
                prompt="Tell me a short joke about databases",
                forbidden_tools=("search_docs", "delete_document"),
            ),
        ],
    )

    assert report["failed"] == 0
    assert report["pass_rate"] == 1.0


def test_injectable_selector_exposes_false_activation():
    def bad_selector(prompt, tools):
        return ["delete_document"]

    report = run_invocation_evals(
        TOOLS,
        [
            InvocationCase(
                case_id="must-not-delete",
                prompt="Search the docs for authentication help",
                expected_tools=("search_docs",),
                forbidden_tools=("delete_document",),
            )
        ],
        selector=bad_selector,
        runner_name="bad-runner-fixture",
    )

    assert report["failed"] == 1
    case = report["cases"][0]
    assert case["missing_expected"] == ["search_docs"]
    assert case["forbidden_selected"] == ["delete_document"]
