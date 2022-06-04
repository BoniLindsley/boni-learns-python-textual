# /usr/bin/env python

# Standard libraries.
import collections.abc
import asyncio
import pathlib
import shutil
import sys
import typing

# External dependencies.
import rich.console
import rich.text
import textual.app
import textual.events
import textual.widget
import textual.widgets

_T = typing.TypeVar("_T")


class MessageArea(textual.widget.Widget):
    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__(*args, **kwargs)
        self._text = rich.text.Text()

    def render(self) -> rich.console.RenderableType:
        return self._text

    async def on_focus(self, event: textual.events.Focus) -> None:
        del event
        self._text.set_length(0)
        self.refresh()

    async def on_key(self, event: textual.events.Key) -> None:
        key = event.key
        if key == "enter":
            await self.app.set_focus(None)
            await self.process_command()
            event.stop()
        elif key.isprintable():
            self._text.append(key)
            self.refresh()
            event.stop()

    async def process_command(self) -> None:
        if self._text.plain == ":q":
            await self.app.action("quit")


class TreeControl(textual.widgets.TreeControl[_T]):
    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__(*args, **kwargs)
        self.show_cursor = True

    def watch_show_cursor(self, value: bool) -> None:
        if value:
            self.hover_node = self.cursor
        super().watch_show_cursor(value)

    def watch_cursor_line(self, value: int) -> None:
        if self.show_cursor:
            self.hover_node = self.cursor
        super().watch_cursor_line(value)

    async def handle_tree_click(self, message: textual.widgets.TreeClick[_T]) -> None:
        node = message.node
        if node.children:
            await node.toggle()

    async def remove(self, node_id: textual.widgets.NodeID) -> None:
        """
        :raise KeyError: If there are no nodes with given ID.
        """
        assert node_id != self.root.id, "Cannot remove root node."
        node = self.nodes.pop(node_id)
        parent = node.parent
        assert parent is not None
        parent.children.remove(node)
        parent.tree.children.remove(node.tree)


class DirectoryTree(TreeControl[pathlib.Path]):
    def __init__(
        self, *args: typing.Any, directory: pathlib.Path, **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, label=directory.name, data=directory, **kwargs)

    async def on_mount(self) -> None:
        message = textual.widgets.TreeClick[pathlib.Path](sender=self, node=self.root)
        await self.handle_tree_click(message=message)

    async def handle_tree_click(
        self, message: textual.widgets.TreeClick[pathlib.Path]
    ) -> None:
        node = message.node
        if not node.children:
            hovered_path = node.data
            if hovered_path.is_dir():
                for path in hovered_path.iterdir():
                    await node.add(label=path.name, data=path)
        await super().handle_tree_click(message)


class ControlPanel(TreeControl[str]):
    _server_runner: collections.abc.AsyncGenerator[None, None]
    _server_node: textual.widgets.TreeNode[str]
    _client_node: textual.widgets.TreeNode[str]
    _rclone_path_node: textual.widgets.TreeNode[str]

    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__(*args, label="rclone rc", data="", **kwargs)

    async def on_mount(self) -> None:
        self._server_runner = self._run_server()
        root = self.root
        await root.add(label="Server: ...", data="")
        self._server_node = self.nodes[self.id]
        await root.add(label="Client: ...", data="")
        self._client_node = self.nodes[self.id]
        await root.add(label="rclone path: ...", data="")
        self._rclone_path_node = self.nodes[self.id]
        await root.expand()

    async def handle_tree_click(self, message: textual.widgets.TreeClick[str]) -> None:
        node = message.node
        if node is self._server_node:
            await self._server_runner.asend(None)

    async def _run_server(self) -> collections.abc.AsyncGenerator[None, None]:
        rclone_path_node = self._rclone_path_node
        server_node = self._server_node
        while True:
            rclone_path: str | None = rclone_path_node.data
            if not rclone_path:
                rclone_path = shutil.which("rclone")
                if rclone_path is None:
                    server_node.label = "Server: Cannot find rclone binary."
                    self.refresh()
                    yield
                    continue
                rclone_path_node.data = rclone_path
                rclone_path_node.label = "rclone path: " + rclone_path
            server_node.label = "Server: Starting."
            self.refresh()
            server_subprocess = await asyncio.create_subprocess_exec(
                rclone_path, "rcd", stderr=asyncio.subprocess.PIPE
            )
            try:
                stderr = server_subprocess.stderr
                assert stderr is not None
                first_line = await stderr.readline()
                expected_line = b" NOTICE: Serving remote control on "
                if expected_line in first_line:
                    server_node.label = "Server: Started."
                else:
                    server_node.label = "Server: Started but may be incompatible."
                self.refresh()
                yield
            finally:
                server_node.label = "Server: Stopping."
                self.refresh()
                server_subprocess.kill()
            server_node.label = "Server: Stopped."
            self.refresh()
            yield


class App(textual.app.App):
    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__(*args, **kwargs)
        self._control_panel = ControlPanel()
        self._file_tree = DirectoryTree(directory=pathlib.Path.home().resolve())
        self._message_area = MessageArea()

    async def on_key(self, event: textual.events.Key) -> None:
        if event.key == ":":
            message_area = self._message_area
            await message_area.focus()
            await message_area.forward_event(event)
        if event.key == "q":
            await self.action("quit")
            event.stop()

    async def on_mount(self) -> None:
        await self.view.dock(self._control_panel, self._file_tree, edge="top")
        await self.view.dock(self._message_area, edge="bottom", size=1, z=1)
        await self._control_panel.focus()


async def async_main() -> int:
    await App().process_messages()
    return 0


def main() -> int:
    return asyncio.run(async_main())


if __name__ == "__main__":
    sys.exit(main())
