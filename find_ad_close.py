import xml.etree.ElementTree as ET
import re

def parse_bounds(bounds_str):
    match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds_str)
    if match:
        return [int(x) for x in match.groups()]
    return None

tree = ET.parse('page_data/ad_page.xml')
for node in tree.getroot().iter('node'):
    if node.attrib.get('content-desc') == 'Ad closed' or node.attrib.get('content-desc') == 'Close ad' or node.attrib.get('content-desc') == 'Close':
        bounds = parse_bounds(node.attrib.get('bounds', ''))
        print(f"Found Close Button at: {bounds}")
