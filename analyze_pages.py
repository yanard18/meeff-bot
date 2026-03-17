import os
import xml.etree.ElementTree as ET
from collections import defaultdict

def extract_identifiers(xml_file):
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        identifiers = set()
        for node in root.iter('node'):
            res_id = node.attrib.get('resource-id', '')
            text = node.attrib.get('text', '')
            if res_id:
                identifiers.add(f"id:{res_id.split('/')[-1]}")
            if text:
                identifiers.add(f"text:{text}")
        return identifiers
    except Exception as e:
        print(f"Error parsing {xml_file}: {e}")
        return set()

def main():
    data_dir = 'page_data'
    files = [f for f in os.listdir(data_dir) if f.endswith('.xml')]
    
    page_identifiers = {}
    for f in files:
        page_name = f.replace('.xml', '')
        page_identifiers[page_name] = extract_identifiers(os.path.join(data_dir, f))
        
    print("--- Unique Identifiers per Page ---")
    for page, ids in page_identifiers.items():
        unique_ids = set(ids)
        for other_page, other_ids in page_identifiers.items():
            if page != other_page:
                unique_ids -= other_ids
                
        print(f"\n{page.upper()}:")
        # Print top 5 unique identifiers to keep output clean
        for uid in list(unique_ids)[:5]:
            print(f"  - {uid}")

if __name__ == '__main__':
    main()

