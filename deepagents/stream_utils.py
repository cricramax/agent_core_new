from __future__ import annotations

from typing import Any, Callable, Dict, Optional


# UI visibility config shared between main and sub-agents
UI_VISIBILITY: Dict[str, Any] = {
    "hide_tool_calls_for": {
        "read_file_content",
        "read_file_content_and_history",
        "ls",
        "write_todos",
    },
    "show_todos_updates": True,
    "show_file_updates": True,
}


def init_stream_state() -> Dict[str, Any]:
    return {
        "buffered_text": "",
        "tool_call_chunks": {},  # idx -> {name, args}
        "printed_tool_calls": set(),
        "last_files_snapshot": None,
    }


def _print_delta_text(current: str, state: Dict[str, Any], print_fn: Callable[[str], None]) -> None:
    buffered_text: str = state["buffered_text"]
    max_lcp = min(len(buffered_text), len(current))
    i = 0
    while i < max_lcp and buffered_text[i] == current[i]:
        i += 1
    delta = current[i:]
    if delta:
        print_fn(delta)
    state["buffered_text"] = current


def handle_messages_chunk(message_chunk: Any, state: Dict[str, Any], ui: Dict[str, Any], print_fn: Callable[[str], None]) -> None:
    if hasattr(message_chunk, "content") and message_chunk.content:
        if getattr(message_chunk, "type", None) == "tool":
            # Skip printing tool message content
            pass
        else:
            _print_delta_text(str(message_chunk.content), state, lambda s: print_fn(s, end="", flush=True))

    addkw = getattr(message_chunk, "additional_kwargs", {}) or {}

    # Assemble partial tool_call chunks by index
    for chunk_tc in (addkw.get("tool_call_chunks") or []):
        idx = chunk_tc.get("index", 0)
        buf = state["tool_call_chunks"].setdefault(idx, {"name": None, "args": ""})
        if chunk_tc.get("name"):
            buf["name"] = chunk_tc["name"]
        if chunk_tc.get("args"):
            buf["args"] += chunk_tc["args"]

    # Also accumulate from tool_calls entries which may stream partials via arguments/name
    for tc in (addkw.get("tool_calls") or []):
        idx = tc.get("index", 0)
        func = tc.get("function") or {}
        name = func.get("name") or tc.get("name")
        args = func.get("arguments") or tc.get("args")
        buf = state["tool_call_chunks"].setdefault(idx, {"name": None, "args": ""})
        if name:
            buf["name"] = name
        if args:
            buf["args"] += args

    # If model indicates tool_calls finish, flush assembled chunked calls (respect visibility config)
    finish_reason = getattr(message_chunk, "response_metadata", {}).get("finish_reason")
    if finish_reason in ("tool_calls", "stop"):
        for idx in sorted(state["tool_call_chunks"].keys()):
            buf = state["tool_call_chunks"][idx]
            if buf.get("name") and buf.get("args"):
                if buf["name"] in ui["hide_tool_calls_for"]:
                    continue
                sig = f"{buf['name']}|{buf['args']}"
                if sig not in state["printed_tool_calls"]:
                    print_fn(f"\n🔧 调用工具: {buf['name']}")
                    print_fn(f"   参数: {buf['args']}")
                    state["printed_tool_calls"].add(sig)
        state["tool_call_chunks"].clear()

    # On assistant stop, print separator
    if finish_reason == "stop":
        print_fn("\n" + "-" * 32)


def handle_updates_chunk(data: Any, state: Dict[str, Any], ui: Dict[str, Any], print_fn: Callable[[str], None]) -> None:
    try:
        if isinstance(data, dict):
            for node_name, node_data in data.items():
                if not isinstance(node_data, dict):
                    continue
                if ui.get("show_todos_updates") and node_data.get("todos"):
                    todos = node_data["todos"]
                    print_fn("\n📋 待办事项已更新：")
                    for i, td in enumerate(todos, 1):
                        title = td.get("content") if isinstance(td, dict) else str(td)
                        status = td.get("status") if isinstance(td, dict) else None
                        if status:
                            print_fn(f"  {i}. [{status}] {title}")
                        else:
                            print_fn(f"  {i}. {title}")
                if ui.get("show_file_updates") and node_data.get("files"):
                    files = node_data["files"]
                    file_list = list(files.keys())
                    if file_list:
                        print_fn("\n🗂️ 工作区文件已更新：")
                        if state["last_files_snapshot"] is not None:
                            new_files = [f for f in file_list if f not in state["last_files_snapshot"]]
                            if new_files:
                                print_fn("  新增:")
                                for f in new_files:
                                    print_fn(f"   - {f}")
                            print_fn("  全部文件：")
                            for f in file_list:
                                print_fn(f"   - {f}")
                        else:
                            for f in file_list:
                                print_fn(f"  - {f}")
                        state["last_files_snapshot"] = set(file_list)
        else:
            print_fn(str(data))
    except Exception:
        print_fn(str(data))


def handle_subagent_event(
    event: Dict[str, Any],
    subagent_states: Dict[str, Dict[str, Any]],
    ui: Dict[str, Any],
    print_fn: Callable[[str], None],
) -> None:
    et = event.get("type")
    if et == "start":
        name = event.get("name") or "subagent"
        if name not in subagent_states:
            subagent_states[name] = init_stream_state()
        print_fn(f"\n=== 启动子智能体: {name} ===")
        if event.get("description"):
            print_fn(f"任务描述: {event['description']}")
        return

    if et == "stop":
        print_fn("\n=== 子智能体任务完成 ===")
        return

    if et == "chunk":
        name = event.get("name") or "subagent"
        if name not in subagent_states:
            subagent_states[name] = init_stream_state()
        sub_state = subagent_states[name]
        stream_type = event.get("stream_type")
        data = event.get("data")
        if stream_type == "messages":
            # data is a tuple (message_chunk, metadata) per upstream format
            message_chunk, _metadata = data
            handle_messages_chunk(message_chunk, sub_state, ui, print_fn)
        elif stream_type == "updates":
            handle_updates_chunk(data, sub_state, ui, print_fn)
        elif stream_type == "custom":
            # For nested custom events inside sub-agent, print raw
            print_fn(str(data))
        return

    # Backward-compatibility: legacy 'content' and 'tool_call'
    if et == "content":
        txt = event.get("text", "")
        if txt and event.get("message_type") != "tool":
            print_fn(txt)
        return
    if et == "tool_call":
        name = event.get("name")
        args = event.get("args")
        if name:
            print_fn(f"\n  🔧 子智能体调用工具: {name}")
            if args is not None:
                print_fn(f"     参数: {args}")


def process_stream_chunk(
    stream_type: str,
    data: Any,
    main_state: Dict[str, Any],
    subagent_states: Dict[str, Dict[str, Any]],
    ui: Dict[str, Any],
    print_fn: Callable[[str], None],
) -> None:
    if stream_type == "messages":
        message_chunk, _metadata = data
        handle_messages_chunk(message_chunk, main_state, ui, print_fn)
    elif stream_type == "updates":
        handle_updates_chunk(data, main_state, ui, print_fn)
    elif stream_type == "custom":
        try:
            if isinstance(data, dict) and "subagent" in data:
                handle_subagent_event(data["subagent"], subagent_states, ui, print_fn)
            else:
                print_fn(str(data))
        except Exception:
            print_fn(str(data))
    else:
        # Unknown type; print raw
        print_fn(str(data))


