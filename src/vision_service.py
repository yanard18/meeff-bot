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
        if not self.cached_tree:
            return False
            
        # If any node belongs to the Meeff package, the app is open
        for node in self.cached_tree.iter('node'):
            if node.attrib.get('package') == self.package_name:
                return True
        return False

    def is_swipe_mode(self):
        """Checks if the app is currently in the swipe/discovery mode."""
        if not self.cached_tree:
            return False
            
        # In the previous dump, we found a button called 'like_imageview' in swipe mode.
        # This is a strong indicator we are looking at a profile.
        for node in self.cached_tree.iter('node'):
            res_id = node.attrib.get('resource-id', '')
            if 'like_imageview' in res_id or 'nope_imageview' in res_id:
                return True
        return False

    def determine_app_state(self):
        """High-level method to determine the overall app state."""
        success = self.refresh_screen_data()
        if not success:
            return "UNKNOWN (Failed to read screen)"

        if not self.is_app_open():
            return "NOT OPENED"
            
        # Collect all resource IDs currently on screen
        res_ids = set()
        for node in self.cached_tree.iter('node'):
            res_id = node.attrib.get('resource-id', '')
            if res_id:
                res_ids.add(res_id.split('/')[-1])
                
        # Identify the page based on unique fingerprints
        if 'action_layout' in res_ids or 'like_imageview' in res_ids:
            return "ACTIVE (Swipe Mode)"
        if 'voice_bloom_imageview' in res_ids or 'vibe_meet_imageview' in res_ids:
            return "ACTIVE (Find Page)"
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
