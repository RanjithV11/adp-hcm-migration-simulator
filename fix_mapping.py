with open('src/transform/mapping_engine.py', 'w') as f:
    f.write(r'''
# Core transformation logic - reads mapping CSV, applies rules
import pandas as pd
import csv
from datetime import datetime
from src.transform.lookups import lookup_cache
from src.transform.encryption import encrypt_ssn

class MappingEngine:
    def __init__(self, mapping_file="config/mapping_document.csv"):
        self.mappings = self._load_mappings(mapping_file)
        self.stats = {"processed": 0, "errors": 0, "warnings": 0}
        self.error_log = []
    
    def _load_mappings(self, file):
        mappings = []
        with open(file, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                mappings.append(row)
        return mappings
    
    def transform_employee(self, emp_row):
        result = {}
        errors = []
        
        for m in self.mappings:
            if m["source_table"] != "legacy_hr.employees":
                continue
            
            src_field = m["source_field"]
            tgt_field = m["target_field"]
            rule = m["transform_rule"]
            validation = m["validation_rule"]
            exception = m["exception_handling"]
            
            try:
                value = emp_row.get(src_field)
                transformed = self._apply_rule(rule, value, emp_row)
                
                if not self._validate(transformed, validation, tgt_field):
                    if "REJECT" in exception:
                        errors.append(f"{tgt_field}: validation failed ({validation})")
                        continue
                    elif "DEFAULT" in exception:
                        transformed = self._get_default(exception)
                    elif "SET_NULL" in exception:
                        transformed = None
                    elif "LOG" in exception:
                        self.stats["warnings"] += 1
                        self.error_log.append(f"WARN: {tgt_field}={value} failed validation")
                
                result[tgt_field] = transformed
                
            except Exception as e:
                self.stats["errors"] += 1
                if "REJECT" in exception:
                    errors.append(f"{tgt_field}: {str(e)}")
                else:
                    result[tgt_field] = None
        
        self.stats["processed"] += 1
        return result, errors
    
    def _apply_rule(self, rule, value, row):
        if not rule or rule == "":
            return value
        
        if rule.startswith("TRIM"):
            return value.strip() if value else value
        if rule.startswith("UPPER"):
            return value.upper() if value else value
        if rule.startswith("LOWER"):
            return value.lower() if value else value
        if rule.startswith("INITCAP"):
            return value.title() if value else value
        
        if "TO_DATE" in rule:
            if not value:
                return None
            if isinstance(value, str):
                for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"]:
                    try:
                        return datetime.strptime(value, fmt).date()
                    except:
                        continue
            return value
        
        if "TO_TIMESTAMP" in rule:
            return value
        
        if rule.startswith("MAP_STATUS"):
            mapping = lookup_cache.get_status_mapping()
            return mapping.get(value, "ACTIVE")
        
        if rule.startswith("LOOKUP_DEPT"):
            mapping = lookup_cache.get_dept_mapping()
            return mapping.get(value)
        
        if rule.startswith("LOOKUP_JOB"):
            mapping = lookup_cache.get_job_mapping()
            return mapping.get(value)
        
        if rule.startswith("LOOKUP_MANAGER"):
            mapping = lookup_cache.get_manager_mapping()
            return mapping.get(value)
        
        if rule.startswith("CONVERT_CURRENCY"):
            salary = row.get("salary_numeric")
            currency = row.get("currency_cd", "USD")
            if currency == "INR":
                rate = lookup_cache.get_currency_rate("INR", "USD")
                return round(float(salary) * rate, 2) if salary else None
            return float(salary) if salary else None
        
        if rule.startswith("ENCRYPT_SSN"):
            return encrypt_ssn(value)
        
        return value
    
    def _validate(self, value, rule, field):
        if not rule or rule == "NULLABLE":
            return True
        
        if "NOT NULL" in rule and (value is None or value == ""):
            return False
        
        if "UNIQUE" in rule:
            return True
        
        if "LEN<=" in rule:
            max_len = int(rule.split("<=")[1].split(",")[0])
            return value is None or len(str(value)) <= max_len
        
        if "RANGE" in rule:
            parts = rule.split(" ")[1].split("-")
            min_v, max_v = float(parts[0]), float(parts[1])
            return value is None or (min_v <= float(value) <= max_v)
        
        if "IN" in rule:
            inner = rule.split("(")[1].split(")")[0]
            allowed = [x.strip().strip('\'').strip('"') for x in inner.split(",")]
            return value is None or value.strip() in allowed
        
        if "FORMAT EMAIL" in rule:
            return value is None or ("@" in str(value) and "." in str(value))
        
        if "FORMAT SSN" in rule:
            return True
        
        if "AGE 18-100" in rule:
            if not value:
                return True
            from datetime import date
            today = date.today()
            age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
            return 18 <= age <= 100
        
        return True
    
    def _get_default(self, exception):
        if "DEFAULT" in exception:
            parts = exception.split("'")
            if len(parts) >= 2:
                return parts[1]
        return None
''')
print('mapping_engine.py fixed')
