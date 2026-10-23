from __future__ import annotations

import re
from typing import Any


# Typed framework/NEST effects. These classifications require compiler-resolved callee/receiver type
# evidence and are therefore stronger than receiver-name heuristics in the fallback source parser.
TYPE_METHOD_EFFECTS: dict[tuple[str, str], tuple[str, str, str]] = {
    ("QFile", "write"): ("filesystem_write", "filesystem", "write"),
    ("QFile", "remove"): ("filesystem_write", "filesystem", "write"),
    ("QFile", "rename"): ("filesystem_write", "filesystem", "write"),
    ("QFile", "copy"): ("filesystem_write", "filesystem", "write"),
    ("QSaveFile", "write"): ("filesystem_write", "filesystem", "write"),
    ("QSaveFile", "commit"): ("filesystem_commit", "filesystem", "write"),
    ("QDir", "mkpath"): ("filesystem_write", "filesystem", "write"),
    ("QDir", "remove"): ("filesystem_write", "filesystem", "write"),
    ("QDir", "rename"): ("filesystem_write", "filesystem", "write"),
    ("QSettings", "setValue"): ("settings_write", "settings", "write"),
    ("QSettings", "remove"): ("settings_write", "settings", "write"),
    ("QSettings", "clear"): ("settings_write", "settings", "write"),
    ("QSettings", "sync"): ("settings_sync", "settings", "write"),
    ("QSettings", "value"): ("settings_read", "settings", "read"),
    ("QSettings", "contains"): ("settings_read", "settings", "read"),
    ("QClipboard", "setText"): ("clipboard_write", "clipboard", "write"),
    ("QClipboard", "setMimeData"): ("clipboard_write", "clipboard", "write"),
    ("QClipboard", "text"): ("clipboard_read", "clipboard", "read"),
    ("QClipboard", "mimeData"): ("clipboard_read", "clipboard", "read"),
    ("QProcess", "start"): ("subprocess_launch", "subprocess", "outbound"),
    ("QProcess", "startDetached"): ("subprocess_launch", "subprocess", "outbound"),
    ("QProcess", "execute"): ("subprocess_launch", "subprocess", "outbound"),
    ("QNetworkAccessManager", "get"): ("network_request", "network", "outbound"),
    ("QNetworkAccessManager", "post"): ("network_request", "network", "outbound"),
    ("QNetworkAccessManager", "put"): ("network_request", "network", "outbound"),
    ("QNetworkAccessManager", "deleteResource"): ("network_request", "network", "outbound"),
    ("QNetworkAccessManager", "sendCustomRequest"): ("network_request", "network", "outbound"),
    ("QLocalSocket", "connectToServer"): ("ipc_connect", "ipc", "outbound"),
    ("QLocalSocket", "write"): ("ipc_send", "ipc", "outbound"),
    ("QLocalServer", "listen"): ("ipc_listen", "ipc", "inbound"),
    ("QPrinter", "newPage"): ("print_job", "printing", "outbound"),
    ("QFileDevice", "permissions"): ("permission_check", "permissions", "read"),
    ("QFileDevice", "setPermissions"): ("permission_change", "permissions", "write"),
    ("QFileInfo", "isReadable"): ("permission_check", "permissions", "read"),
    ("QFileInfo", "isWritable"): ("permission_check", "permissions", "read"),
    ("QFileInfo", "isExecutable"): ("permission_check", "permissions", "read"),
    ("QSaveFile", "cancelWriting"): ("persistence_cancel", "filesystem", "write"),
    ("QLockFile", "tryLock"): ("file_lock_acquire", "filesystem", "write"),
    ("QLockFile", "unlock"): ("file_lock_release", "filesystem", "write"),
    ("QLockFile", "isLocked"): ("file_lock_state", "filesystem", "read"),
    ("QProcess", "terminate"): ("subprocess_cancel", "subprocess", "outbound"),
    ("QProcess", "kill"): ("subprocess_cancel", "subprocess", "outbound"),
    ("QProcess", "waitForFinished"): ("subprocess_wait", "subprocess", "read"),
    ("QProcess", "error"): ("subprocess_error_state", "subprocess", "read"),
    ("QProcess", "exitCode"): ("subprocess_exit_state", "subprocess", "read"),
    ("QNetworkReply", "abort"): ("network_cancel", "network", "outbound"),
    ("QNetworkReply", "error"): ("network_error_state", "network", "read"),
    ("QNetworkReply", "errorString"): ("network_error_state", "network", "read"),
    ("QLocalSocket", "abort"): ("ipc_cancel", "ipc", "outbound"),
    ("QLocalSocket", "disconnectFromServer"): ("ipc_disconnect", "ipc", "outbound"),
    ("QSettings", "status"): ("settings_status", "settings", "read"),
}

TYPE_METHOD_FEEDBACK: dict[tuple[str, str], str] = {
    ("QStatusBar", "showMessage"): "status_message",
    ("QWidget", "setWindowTitle"): "window_title",
    ("QWidget", "setToolTip"): "tooltip_property",
    ("QMessageBox", "information"): "modal_message",
    ("QMessageBox", "warning"): "modal_message",
    ("QMessageBox", "critical"): "modal_message",
    ("QMessageBox", "question"): "modal_question",
    ("QMessageBox", "about"): "modal_message",
}

TYPE_METHOD_RECEPTORS: dict[tuple[str, str], tuple[str, bool]] = {
    ("QPluginLoader", "load"): ("qt_plugin", False),
    ("QPluginLoader", "unload"): ("qt_plugin", False),
    ("QPluginLoader", "instance"): ("qt_plugin", True),
    ("QPluginLoader", "setFileName"): ("qt_plugin", False),
    ("QLibrary", "load"): ("dynamic_library", False),
    ("QLibrary", "unload"): ("dynamic_library", False),
    ("QLibrary", "resolve"): ("dynamic_library", True),
    ("QJSEngine", "evaluate"): ("javascript", True),
}

GLOBAL_FUNCTION_EFFECTS: dict[str, tuple[str, str, str]] = {
    "qEnvironmentVariable": ("environment_read", "environment", "read"),
    "qEnvironmentVariableIsSet": ("environment_read", "environment", "read"),
    "qputenv": ("environment_write", "environment", "write"),
    "qunsetenv": ("environment_write", "environment", "write"),
    "getenv": ("environment_read", "environment", "read"),
}

GLOBAL_FUNCTION_RECEPTORS: dict[str, tuple[str, bool]] = {
    "luaL_loadfile": ("lua", True),
    "luaL_loadfilex": ("lua", True),
    "luaL_loadstring": ("lua", True),
    "luaL_dofile": ("lua", True),
    "lua_pcall": ("lua", False),
    "lua_pcallk": ("lua", False),
}


def normalize_cpp_type(qual_type: str | None) -> str | None:
    if not qual_type:
        return None
    t = str(qual_type)
    t = re.sub(r"\b(const|volatile|class|struct)\b", "", t)
    t = re.sub(r"[\*&]+", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    # For templates keep the outer provider type; namespaces are retained until final component.
    outer = t.split("<", 1)[0].strip()
    return outer.rsplit("::", 1)[-1] if outer else None


def classify_typed_call(*, qualified_name: str | None, receiver_static_type: str | None,
                        callee_name: str | None) -> dict[str, Any] | None:
    method = callee_name or (qualified_name.rsplit("::", 1)[-1] if qualified_name else None)
    if not method:
        return None
    owner = None
    if qualified_name and "::" in qualified_name:
        owner = qualified_name.rsplit("::", 1)[0].rsplit("::", 1)[-1]
    receiver_owner = normalize_cpp_type(receiver_static_type)
    for candidate in (receiver_owner, owner):
        if candidate and (candidate, method) in TYPE_METHOD_EFFECTS:
            effect, capability, direction = TYPE_METHOD_EFFECTS[(candidate, method)]
            return {"kind": "effect", "effect_type": effect, "capability": capability,
                    "direction": direction, "owner_type": candidate, "method": method}
        if candidate and (candidate, method) in TYPE_METHOD_FEEDBACK:
            return {"kind": "feedback", "feedback_type": TYPE_METHOD_FEEDBACK[(candidate, method)],
                    "owner_type": candidate, "method": method}
        if candidate and (candidate, method) in TYPE_METHOD_RECEPTORS:
            receptor_type, factory = TYPE_METHOD_RECEPTORS[(candidate, method)]
            return {"kind": "extension", "receptor_type": receptor_type, "factory": factory,
                    "owner_type": candidate, "method": method}
    if method in GLOBAL_FUNCTION_EFFECTS:
        effect, capability, direction = GLOBAL_FUNCTION_EFFECTS[method]
        return {"kind": "effect", "effect_type": effect, "capability": capability,
                "direction": direction, "owner_type": "global", "method": method}
    if method in GLOBAL_FUNCTION_RECEPTORS:
        receptor_type, factory = GLOBAL_FUNCTION_RECEPTORS[method]
        return {"kind": "extension", "receptor_type": receptor_type, "factory": factory,
                "owner_type": "global", "method": method}
    return None
