import json

from kavi_capability_compiler.config import sanitize_mcp_config


def test_config_summary_never_persists_env_header_or_url_secret_values():
    config={
        "mcpServers":{
            "local":{
                "command":"/Users/alice/bin/npx",
                "args":["-y","@vendor/server","--token=literal-secret","\${API_KEY}"],
                "env":{"API_KEY":"super-secret","PASSWORD":"another-secret"},
            },
            "remote":{
                "url":"https://user:pass@example.com/mcp?token=query-secret&tenant=acme",
                "headers":{"Authorization":"Bearer header-secret","X-Tenant":"acme"},
            },
        }
    }
    result=sanitize_mcp_config(config)
    text=json.dumps(result)
    for secret in ["super-secret","another-secret","literal-secret","query-secret","header-secret","user","pass","alice","acme"]:
        assert secret not in text
    local=next(x for x in result["servers"] if x["name"]=="local")
    remote=next(x for x in result["servers"] if x["name"]=="remote")
    assert local["command"]=="npx"
    assert local["env_keys"]==["API_KEY","PASSWORD"]
    assert local["args"]==["-y","<arg>","--token=<redacted>","<env-ref>"]
    assert remote["url"]=="https://example.com/mcp"
    assert remote["query_keys"]==["tenant","token"]
    assert remote["header_names"]==["Authorization","X-Tenant"]
    assert remote["had_userinfo"] is True
