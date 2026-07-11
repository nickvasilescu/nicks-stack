# Hermes plugin: orgo-desktop-local

## Official pattern

Docs:

- https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins
- https://hermes-agent.nousresearch.com/docs/guides/build-a-hermes-plugin
- Bundled reference: `plugins/spotify` (`ctx.register_tool` + toolset + check_fn)
- Core: `hermes_cli/plugins.py` → `PluginContext.register_tool` → `tools.registry`

Layout:

```text
~/.hermes/plugins/orgo-desktop-local/
  plugin.yaml
  __init__.py    # register(ctx)
  tools.py       # schemas + handlers
```

User plugins are **opt-in**:

```bash
hermes plugins enable orgo-desktop-local
hermes tools enable orgo_desktop --platform cli
```

Config effects:

- `plugins.enabled` includes `orgo-desktop-local`
- `platform_toolsets.<platform>` includes `orgo_desktop`
  (enabling may expand composites like `hermes-cli` into explicit toolset lists)

**Full process restart required** for the model to see new tools (not only `/new` on a process that started before enable).

## Tool count (v1.1+)

doctor, screenshot, click, **drag**, **click_path**, type, key, bash, scroll, open_url, wait.

Click / drag / click_path support visual verify via client fingerprinting.

## check_fn

Handlers gate on `is_colocated()` → `GET http://127.0.0.1:8080/health` healthy.
If false, tools stay registered but should not dispatch successfully for GUI work
on non-Orgo hosts.

## Agent config edits

Hermes agents often **cannot** write `~/.hermes/config.yaml` via file tools
(security soft-guard). Use CLI:

```bash
hermes plugins enable <name>
hermes tools enable <toolset> --platform <platform>
hermes config set <key> <value>
```

## Do not

- Do not use `override=True` to replace built-ins without
  `plugins.entries.<id>.allow_tool_override: true`
- Do not treat mid-session `plugins enable` as hot-load
