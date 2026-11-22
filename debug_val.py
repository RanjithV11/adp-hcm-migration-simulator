from src.transform.mapping_engine import MappingEngine

engine = MappingEngine()

from src.extract.legacy_extractor import extract_employees
data = extract_employees()
sample = data.iloc[0].to_dict()

m = None
for mapping_item in engine.mappings:
    if mapping_item['source_field'] == 'status_code':
        m = mapping_item
        break

print('Validation rule:', repr(m['validation_rule']))
print('Exception handling:', repr(m['exception_handling']))

value = 'ACTIVE'
validation = m['validation_rule']
print('Validation contains IN:', 'IN' in validation)

inner = validation.split('(')[1].split(')')[0]
print('Inner:', inner)
allowed = [x.strip().strip('"').strip("'") for x in inner.split(',')]
print('Allowed:', allowed)
print('Value in allowed:', value in allowed)
