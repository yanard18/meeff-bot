import xml.etree.ElementTree as ET
import re

def parse_bounds(bounds_str):
    match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds_str)
    if match:
        return [int(x) for x in match.groups()]
    return None

tree = ET.parse('page_data/swipe_page.xml')
for node in tree.getroot().iter('node'):
    res_id = node.attrib.get('resource-id', '')
    if 'profile' in res_id.lower() or 'photo' in res_id.lower():
        bounds = parse_bounds(node.attrib.get('bounds', ''))
        if bounds and bounds[2] - bounds[0] > 500: # Only look for large main elements
            print(f"Found on swipe page: {res_id} at {bounds}")
