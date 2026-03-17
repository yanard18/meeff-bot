import xml.etree.ElementTree as ET
tree = ET.parse('page_data/ad_page.xml')
for node in tree.getroot().iter('node'):
    res_id = node.attrib.get('resource-id', '')
    cls = node.attrib.get('class', '')
    text = node.attrib.get('text', '')
    desc = node.attrib.get('content-desc', '')
    if res_id or text or desc or 'WebView' in cls or 'Button' in cls:
        print(f"Class: {cls} | ID: {res_id} | Text: {text} | Desc: {desc}")
