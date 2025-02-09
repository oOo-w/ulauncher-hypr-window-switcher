import subprocess
import json
import os
import logging
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.client.Extension import Extension
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.event import ItemEnterEvent, KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem

logger = logging.getLogger(__name__)


class HyprlandWindowSwitcherExtension(Extension):
    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(ItemEnterEvent, ItemEnterEventListener())


class KeywordQueryEventListener(EventListener):
    def on_event(self, event, extension):
        query = event.get_argument() or str()
        keyword = event.get_keyword()
        if keyword != extension.preferences["switch_kw"]:
            return
        if not query.strip():
            logger.debug("No query, fetching all windows")
            # Retrieve all windows from Hyprland
            windows = get_windows()
            items = [
                ExtensionResultItem(
                    icon="images/icon.svg",
                    name=window["class"] + "\t" + window["title"],
                    description=f"Monitor {window['monitor']}, Workspace {window['workspace']}, PID {window['pid']}",
                    on_enter=ExtensionCustomAction(
                        {
                            "address": window["address"],
                            "workspace": window["workspace"],
                        },
                        keep_app_open=False,
                    ),
                )
                for window in windows
            ]
            return RenderResultListAction(items)
        else:
            # Filter windows based on query
            windows = search_windows(query)
            items = [
                ExtensionResultItem(
                    icon="images/icon.svg",
                    name=window["class"] + "\t" + window["title"],
                    description=f"Workspace {window['workspace']}",
                    on_enter=ExtensionCustomAction(
                        {
                            "address": window["address"],
                            "workspace": window["workspace"],
                        },
                        keep_app_open=False,
                    ),
                )
                for window in windows
            ]
            return RenderResultListAction(items)


class ItemEnterEventListener(EventListener):
    def on_event(self, event, extension):
        data = event.get_data()
        address = data["address"]
        workspace = data["workspace"]
        # Activate the workspace first
        if workspace != 0:
            activate_workspace(workspace)
        # Activate the window
        activate_window(address)
        return RenderResultListAction([])


def get_windows():
    windows = []
    try:
        # Run hyprctl clients to get window information
        result = subprocess.run(
            ["hyprctl", "clients", "-j"], capture_output=True, text=True
        )
        clients = json.loads(result.stdout)
        for client in clients:
            window = {
                "address": client["address"],
                "class": client["class"],
                "title": client["title"],
                "workspace": client["workspace"]["id"],
                "floating": client["floating"],
                "monitor": client["monitor"],
                "pid": client["pid"],
            }
            windows.append(window)
    except Exception as e:
        logger.error(f"Error getting windows: {e}")
    return windows


def search_windows(query):
    windows = get_windows()
    query = query.lower()
    return [
        w
        for w in windows
        if query in w["title"].lower() or query in str(w["workspace"])
    ]


def activate_window(address):
    try:
        subprocess.run(
            ["hyprctl", "dispatch", "focuswindow", f"address:{address}"], check=True
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to focus window: {e}")


def activate_workspace(workspace_id):
    try:
        subprocess.run(
            ["hyprctl", "dispatch", "workspace", str(workspace_id)], check=True
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to focus workspace: {e}")


if __name__ == "__main__":
    HyprlandWindowSwitcherExtension().run()
