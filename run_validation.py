from src.validate.reconciliation import ValidationSuite
import json, os
from datetime import datetime

validator = ValidationSuite()
report = validator.run_all()

os.makedirs('output', exist_ok=True)
report_file = f'output/validation_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
with open(report_file, 'w') as f:
    json.dump(report, f, indent=2, default=str)

for c in report['checks']:
    icon = 'PASS' if c['status'] == 'PASS' else ('WARN' if c['status'] == 'WARN' else 'FAIL')
    print(f'{icon}: {c["name"]} - {c["status"]}')

print(f'Summary: {report["summary"]}')
