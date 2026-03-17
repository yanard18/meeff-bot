import xml.etree.ElementTree as ET
import re

def parse_bounds(bounds_str):
    match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds_str)
    if match:
        return [int(x) for x in match.groups()]
    return None

def find_clickable_elements(xml_file):
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        clickables = []
        for node in root.iter('node'):
            if node.attrib.get('clickable') == 'true':
                res_id = node.attrib.get('resource-id', '').split('/')[-1]
                content_desc = node.attrib.get('content-desc', '')
                text = node.attrib.get('text', '')
                bounds = parse_bounds(node.attrib.get('bounds', ''))
                
                name = res_id or content_desc or text or 'Unknown'
                if bounds:
                    clickables.append({'name': name, 'bounds': bounds})
                    
        return clickables
    except Exception as e:
        print(f"Error parsing XML: {e}")
        return []

if __name__ == '__main__':
    elements = find_clickable_elements('window_dump.xml')
    print("Clickable Elements Found:")
    for el in elements:
        print(f"- Name: {el['name']} | Bounds: {el['bounds']}")
