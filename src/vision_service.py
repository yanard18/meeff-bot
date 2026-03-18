import re
import xml.etree.ElementTree as ET

class VisionService:
    """The 'Eyes' of the bot. Analyzes the UI structure to determine state."""
    
    def __init__(self, adb_service):
        self.adb = adb_service
        self.package_name = "com.noyesrun.meeff.kr"
        self.cached_tree = None

    def refresh_screen_data(self):
        """Pulls a new XML dump from the device and parses it."""
        xml_content = self.adb.get_window_dump()
        if not xml_content:
            self.cached_tree = None
            return False

        try:
            self.cached_tree = ET.fromstring(xml_content)
            return True
        except ET.ParseError as e:
            # print(f"[VisionService] Failed to parse XML: {e}")
            self.cached_tree = None
            return False

    def is_app_open(self):
        """Checks if the Meeff app package is currently rendering on screen."""
        if self.cached_tree is None:
            return False
            
        # If any node belongs to the Meeff package, the app is open
        for node in self.cached_tree.iter('node'):
            if node.attrib.get('package') == self.package_name:
                return True
        return False

    def _parse_bounds(self, node) -> dict | None:
        """Parse an Android bounds string '[x1,y1][x2,y2]' into a dict."""
        m = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', node.attrib.get('bounds', ''))
        if m:
            return {"x_min": int(m.group(1)), "y_min": int(m.group(2)),
                    "x_max": int(m.group(3)), "y_max": int(m.group(4))}
        return None

    def get_node_bounds(self, resource_id_suffix) -> dict | None:
        """Returns the bounds dict of the first node whose resource-id ends with the given suffix."""
        if self.cached_tree is None:
            return None
        for node in self.cached_tree.iter('node'):
            if node.attrib.get('resource-id', '').split('/')[-1] == resource_id_suffix:
                bounds = self._parse_bounds(node)
                if bounds:
                    return bounds
        return None

    def determine_app_state(self):
        """High-level method to determine the overall app state."""
        success = self.refresh_screen_data()
        if not success:
            return "UNKNOWN (Failed to read screen)"

        if not self.is_app_open():
            return "NOT OPENED"
            
        # Collect all resource IDs and content descriptions currently on screen
        res_ids = set()
        descs = set()
        
        for node in self.cached_tree.iter('node'):
            res_id = node.attrib.get('resource-id', '')
            desc = node.attrib.get('content-desc', '')
            if res_id:
                res_ids.add(res_id.split('/')[-1])
            if desc:
                descs.add(desc)
                
        # Dialogs that can overlay any state — handle first
        if 'messageTextView' in res_ids and 'negativeButton' in res_ids:
            return "ACTIVE (Quit Dialog)"
        if 'md_root' in res_ids:
            return "ACTIVE (Suggest Meeff)"
        if 'target_photo_imageview' in res_ids:
            return "ACTIVE (Match Complete)"

        # WebView ad: has an explicit close button with a known content-desc
        if 'Ad closed' in descs or 'Close ad' in descs:
            return "ACTIVE (Ad)"

        # Native ad: embedded ad container (note: app has a typo — "conatiner")
        if 'native_ad_conatiner' in res_ids:
            return "ACTIVE (Native Ad)"
                
        # Identify the page based on unique fingerprints
        if 'force_open_imageview' in res_ids or 'answer_layout' in res_ids:
            return "ACTIVE (Detailed Profile)"
        if 'action_layout' in res_ids or 'like_imageview' in res_ids:
            return "ACTIVE (Swipe Mode)"
        if 'voice_bloom_imageview' in res_ids or 'vibe_meet_imageview' in res_ids:
            return "ACTIVE (Find Page)"
        # Individual chat (has message input field) — check before Chat List
        if 'message_edittext' in res_ids or 'send_imageview' in res_ids:
            return "ACTIVE (Chat With Person)"
        if 'last_msg_textview' in res_ids or 'local_time_textview' in res_ids:
            return "ACTIVE (Chat List)"
        if 'plus_layout' in res_ids or 'ruby_count_textview' in res_ids:
            return "ACTIVE (My Profile)"
        if 'distance_seekbar' in res_ids:
            return "ACTIVE (Search Filters)"
        if 'option_imageview' in res_ids or 'no_result_title_textview' in res_ids:
            return "ACTIVE (Like/Visitor Page)"
        if 'refresh_layout' in res_ids:
            return "ACTIVE (Today Page)"
            
        return "ACTIVE (Unknown Screen/Ad)"

    def get_like_count(self) -> int:
        """Returns the number of incoming likes shown on the Like tab page."""
        if self.cached_tree is None:
            return 0
        for node in self.cached_tree.iter('node'):
            m = re.match(r'^(\d+)\s+Friend', node.attrib.get('text', ''))
            if m:
                return int(m.group(1))
        return 0

    def get_like_inner_tab_bounds(self):
        """Returns bounds of the 'Like' inner tab in the Chat section."""
        if self.cached_tree is None:
            return None
        for node in self.cached_tree.iter('node'):
            if node.attrib.get('clickable') != 'true':
                continue
            for child in node.iter('node'):
                if (child.attrib.get('text') == 'Like' and
                        'title_textview' in child.attrib.get('resource-id', '')):
                    bounds = self._parse_bounds(node)
                    if bounds and bounds['y_min'] < 300:  # must be in the tab-bar area
                        return bounds
        return None

    def get_first_liked_profile_bounds(self):
        """Returns bounds of the first profile thumbnail in the likes grid."""
        return self.get_node_bounds('thumb_photo_imageview')
