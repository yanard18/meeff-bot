import xml.etree.ElementTree as ET
import re

def parse_bounds(bounds_str):
    match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds_str)
    if match:
        return [int(x) for x in match.groups()]
    return None

tree = ET.parse('page_data/detailed_profile.xml')
for node in tree.getroot().iter('node'):
    res_id = node.attrib.get('resource-id', '')
    if 'like' in res_id.lower() or 'nope' in res_id.lower() or 'back' in res_id.lower():
        bounds = parse_bounds(node.attrib.get('bounds', ''))
        print(f"Found: {res_id} at {bounds}")
