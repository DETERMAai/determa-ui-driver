from vscode_extension_bridge import get_editor_state


def get_native_editor_state(ui_state=None):
    return get_editor_state(ui_state)
