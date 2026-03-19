import re
import xml.etree.ElementTree as ET


class VisionService:
    """XML parsing utility for Android UI hierarchies.

    Knows nothing about Meeff, Instagram, or any specific app. It just parses
    the XML dump produced by `adb shell uiautomator dump` and provides generic
    node lookup helpers.

    App-specific state detection and resource-id knowledge live in each
    Platform subclass (e.g. MeeffPlatform), which owns a VisionService and
    calls these helpers to build its answers.
    """

    def __init__(self, adb_service):
        self.adb = adb_service
        self.cached_tree = None
        self._screen_width: int | None = None

    # ------------------------------------------------------------------
    # Screen data
    # ------------------------------------------------------------------

    def refresh_screen_data(self) -> bool:
        """Pull a new XML dump from the device and parse it.

        Returns True on success, False on failure (cached_tree is cleared).
        """
        xml_content = self.adb.get_window_dump()
        if not xml_content:
            self.cached_tree = None
            return False

        try:
            self.cached_tree = ET.fromstring(xml_content)
            return True
        except ET.ParseError as e:
            print(f"[VisionService] Failed to parse XML: {e}")
            self.cached_tree = None
            return False

    # ------------------------------------------------------------------
    # Generic node lookup
    # ------------------------------------------------------------------

    def _parse_bounds(self, node) -> dict | None:
        """Parse '[x1,y1][x2,y2]' into {x_min, y_min, x_max, y_max}."""
        m = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', node.attrib.get('bounds', ''))
        if m:
            return {
                "x_min": int(m.group(1)), "y_min": int(m.group(2)),
                "x_max": int(m.group(3)), "y_max": int(m.group(4)),
            }
        return None

    def get_node_bounds(self, resource_id_suffix: str) -> dict | None:
        """Bounds of the first node whose resource-id ends with suffix."""
        if self.cached_tree is None:
            return None
        for node in self.cached_tree.iter('node'):
            if node.attrib.get('resource-id', '').split('/')[-1] == resource_id_suffix:
                bounds = self._parse_bounds(node)
                if bounds:
                    return bounds
        return None

    def get_node_text(self, resource_id_suffix: str) -> str | None:
        """Text of the first node whose resource-id ends with suffix."""
        if self.cached_tree is None:
            return None
        for node in self.cached_tree.iter('node'):
            if node.attrib.get('resource-id', '').split('/')[-1] == resource_id_suffix:
                text = node.attrib.get('text', '').strip()
                return text if text else None
        return None

    def get_all_node_texts(self, resource_id_suffix: str) -> list[str]:
        """Text from ALL nodes whose resource-id ends with suffix.

        Used for repeated elements like Q&A sections where multiple nodes
        share the same resource-id suffix.
        """
        if self.cached_tree is None:
            return []
        results = []
        for node in self.cached_tree.iter('node'):
            if node.attrib.get('resource-id', '').split('/')[-1] == resource_id_suffix:
                text = node.attrib.get('text', '').strip()
                if text:
                    results.append(text)
        return results

    def get_node_bounds_by_desc(self, content_desc: str) -> dict | None:
        """Bounds of the first node with the given content-desc."""
        if self.cached_tree is None:
            return None
        for node in self.cached_tree.iter('node'):
            if node.attrib.get('content-desc', '') == content_desc:
                bounds = self._parse_bounds(node)
                if bounds:
                    return bounds
        return None

    def collect_resource_ids(self) -> set[str]:
        """Return all resource-id suffixes present in the current tree.

        Used by platform state detectors to fingerprint the current screen.
        """
        if self.cached_tree is None:
            return set()
        return {
            node.attrib['resource-id'].split('/')[-1]
            for node in self.cached_tree.iter('node')
            if node.attrib.get('resource-id')
        }

    def collect_content_descs(self) -> set[str]:
        """Return all non-empty content-desc values in the current tree."""
        if self.cached_tree is None:
            return set()
        return {
            node.attrib['content-desc']
            for node in self.cached_tree.iter('node')
            if node.attrib.get('content-desc')
        }

    def build_parent_map(self) -> dict:
        """Build a child→parent mapping for upward tree traversal."""
        if self.cached_tree is None:
            return {}
        return {
            child: parent
            for parent in self.cached_tree.iter()
            for child in parent
        }

    # ------------------------------------------------------------------
    # Chat message parsing (layout-heuristic, shared across chat apps)
    # ------------------------------------------------------------------

    def get_chat_messages(self, msg_id_suffixes: set[str] | None = None) -> list[dict]:
        """Return visible messages in the current chat screen.

        Each dict: {text, direction}  where direction is 'sent' or 'received'.

        Direction is inferred by x-position relative to the screen midpoint:
        right-aligned bubbles (x_min > midpoint) are sent, left are received.

        Args:
            msg_id_suffixes: resource-id suffixes to treat as message nodes.
                             Defaults to a set of common message IDs.
        """
        if self.cached_tree is None:
            return []

        if msg_id_suffixes is None:
            msg_id_suffixes = {
                'message_textview', 'chat_message_textview',
                'content_textview', 'message_text_textview',
            }

        if self._screen_width is None:
            self._screen_width = self.adb.get_screen_width()
        midpoint = self._screen_width // 2

        messages = []
        for node in self.cached_tree.iter('node'):
            if node.attrib.get('resource-id', '').split('/')[-1] not in msg_id_suffixes:
                continue
            text = node.attrib.get('text', '').strip()
            if not text:
                continue
            bounds = self._parse_bounds(node)
            if not bounds:
                continue
            direction = 'sent' if bounds['x_min'] > midpoint else 'received'
            messages.append({'text': text, 'direction': direction})

        return messages
