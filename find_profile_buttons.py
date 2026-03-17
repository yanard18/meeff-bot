import xml.etree.ElementTree as ET
import re

def parse_bounds(bounds_str):
    match = re.match(r'\\[(\\\\d+),(\\\\d+)\\]\\\[(\\\\d+),(\\\\d+)\\]', bounds_str)
    if match:
        return [int(x) for x in match.groups()]
    return None

def analyze_detailed_profile(xml_file):
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        clickables = []
        identifiers = set()
        
        for node in root.iter('node'):
            res_id = node.attrib.get('resource-id', '')
            if res_id:
                clean_id = res_id.split('/')[-1]
                identifiers.add(clean_id)
                
            if node.attrib.get('clickable') == 'true':
                content_desc = node.attrib.get('content-desc', '')
                text = node.attrib.get('text', '')
                bounds = parse_bounds(node.attrib.get('bounds', ''))
                
                name = clean_id if res_id else content_desc or text or 'Unknown'
                if bounds:
                    clickables.append({'name': name, 'bounds': bounds})
                    
        print("--- Clickable Buttons Found ---")
        for el in clickables:
            if 'like' in el['name'].lower() or 'nope' in el['name'].lower() or 'back' in el['name'].lower() or 'close' in el['name'].lower():
                 print(f"- **IMPORTANT** Name: {el['name']} | Bounds: {el['bounds']}")
            else:
                 print(f"- Name: {el['name']} | Bounds: {el['bounds']}")
                 
        print("\n--- Potential Unique Identifiers ---")
        # Print some IDs that might uniquely identify this page vs the main swipe deck
        for uid in list(identifiers)[:10]:
            print(f"- {uid}")
            
    except Exception as e:
        print(f"Error parsing XML: {e}")

if __name__ == '__main__':
    analyze_detailed_profile('page_data/detailed_profile.xml')
