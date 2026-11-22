from src.utils.db import get_pg_conn, put_pg_conn
import json
from datetime import datetime

class ValidationSuite:
    def __init__(self):
        self.checks = []
    
    def run_all(self):
        report = {
            'run_id': datetime.now().isoformat(),
            'checks': [],
            'summary': {'pass': 0, 'warn': 0, 'fail': 0, 'info': 0}
        }
        
        report['checks'].append(self._check_row_counts())
        report['checks'].append(self._check_salary_totals())
        report['checks'].append(self._check_null_critical())
        report['checks'].append(self._check_dup_ssn())
        report['checks'].append(self._check_fk_orphans())
        report['checks'].append(self._check_business_rules())
        report['checks'].append(self._check_formats())
        report['checks'].append(self._check_status_mapping())
        
        for c in report['checks']:
            report['summary'][c['status'].lower()] += 1
        
        return report
    
    def _run_query(self, query):
        conn = get_pg_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(query)
                return cur.fetchone()[0]
        finally:
            put_pg_conn(conn)
    
    def _check_row_counts(self):
        src = self._run_query("SELECT COUNT(*) FROM legacy_hr.employees")
        tgt = self._run_query("SELECT COUNT(*) FROM adp_hcm.hcm_employee")
        diff = tgt - src
        status = 'PASS' if diff == 0 else ('WARN' if abs(diff) < src * 0.02 else 'FAIL')
        return {
            'name': 'row_count_employee',
            'description': 'Employee row count reconciliation',
            'source_value': src,
            'target_value': tgt,
            'difference': diff,
            'status': status,
            'threshold': '0'
        }
    
    def _check_salary_totals(self):
        src = self._run_query("""
            SELECT SUM(CASE WHEN currency_cd='INR' THEN salary_numeric/83.0 ELSE salary_numeric END)
            FROM legacy_hr.employees
        """)
        tgt = self._run_query("SELECT SUM(annual_salary_usd) FROM adp_hcm.hcm_employee")
        diff_pct = abs(src - tgt) / src * 100 if src else 0
        status = 'PASS' if diff_pct < 0.1 else ('WARN' if diff_pct < 1.0 else 'FAIL')
        return {
            'name': 'total_salary_usd',
            'description': 'Total annual salary (USD normalized)',
            'source_value': round(src, 2) if src else 0,
            'target_value': round(tgt, 2) if tgt else 0,
            'diff_pct': round(diff_pct, 4),
            'status': status,
            'threshold': '<0.1%'
        }
    
    def _check_null_critical(self):
        fields = ['employee_id', 'legal_first_name', 'legal_last_name', 'hire_date', 'worker_status_cd']
        results = {}
        for f in fields:
            cnt = self._run_query(f"SELECT COUNT(*) FROM adp_hcm.hcm_employee WHERE {f} IS NULL")
            results[f] = cnt
        total_nulls = sum(results.values())
        status = 'PASS' if total_nulls == 0 else 'FAIL'
        return {
            'name': 'null_critical_fields',
            'description': 'Null check on critical fields',
            'details': results,
            'total_nulls': total_nulls,
            'status': status,
            'threshold': '0'
        }
    
    def _check_dup_ssn(self):
        cnt = self._run_query("""
            SELECT COUNT(*) FROM (
                SELECT ssn_encrypted FROM adp_hcm.hcm_employee
                WHERE ssn_encrypted IS NOT NULL
                GROUP BY ssn_encrypted HAVING COUNT(*) > 1
            ) t
        """)
        status = 'PASS' if cnt == 0 else 'FAIL'
        return {
            'name': 'dup_ssn',
            'description': 'Duplicate encrypted SSN check',
            'duplicate_count': cnt,
            'status': status,
            'threshold': '0'
        }
    
    def _check_fk_orphans(self):
        checks = [
            ('orphan_dept', 'department_id', 'adp_hcm.hcm_department', 'department_id'),
            ('orphan_job', 'job_id', 'adp_hcm.hcm_job', 'job_id'),
            ('orphan_manager', 'manager_person_id', 'adp_hcm.hcm_employee', 'person_id'),
        ]
        results = {}
        for name, fk_col, ref_table, ref_col in checks:
            cnt = self._run_query(f"""
                SELECT COUNT(*) FROM adp_hcm.hcm_employee e
                LEFT JOIN {ref_table} r ON e.{fk_col} = r.{ref_col}
                WHERE e.{fk_col} IS NOT NULL AND r.{ref_col} IS NULL
            """)
            results[name] = cnt
        total = sum(results.values())
        status = 'PASS' if total == 0 else 'WARN'
        return {
            'name': 'fk_orphans',
            'description': 'Foreign key orphan check',
            'details': results,
            'total_orphans': total,
            'status': status,
            'threshold': '0'
        }
    
    def _check_business_rules(self):
        checks = [
            ('term_no_date', "SELECT COUNT(*) FROM adp_hcm.hcm_employee WHERE worker_status_cd='TERMINATED' AND termination_date IS NULL"),
            ('salary_range', "SELECT COUNT(*) FROM adp_hcm.hcm_employee WHERE annual_salary_usd NOT BETWEEN 15000 AND 500000"),
            ('future_hire', "SELECT COUNT(*) FROM adp_hcm.hcm_employee WHERE hire_date > CURRENT_DATE"),
            ('dob_age', "SELECT COUNT(*) FROM adp_hcm.hcm_employee WHERE date_of_birth IS NOT NULL AND (DATE_PART('year', AGE(CURRENT_DATE, date_of_birth)) < 18 OR DATE_PART('year', AGE(CURRENT_DATE, date_of_birth)) > 100)"),
        ]
        results = {}
        for name, query in checks:
            cnt = self._run_query(query)
            results[name] = cnt
        total = sum(results.values())
        status = 'PASS' if total == 0 else 'WARN'
        return {
            'name': 'business_rules',
            'description': 'Business rule validation',
            'details': results,
            'total_violations': total,
            'status': status,
            'threshold': '0'
        }
    
    def _check_formats(self):
        checks = [
            ('email_format', "SELECT COUNT(*) FROM adp_hcm.hcm_employee WHERE work_email IS NOT NULL AND work_email NOT LIKE '%@%.%'"),
            ('ssn_encrypted', "SELECT COUNT(*) FROM adp_hcm.hcm_employee WHERE ssn_encrypted IS NOT NULL"),
        ]
        results = {}
        for name, query in checks:
            cnt = self._run_query(query)
            results[name] = cnt
        return {
            'name': 'format_validation',
            'description': 'Data format validation',
            'details': results,
            'status': 'INFO',
            'threshold': 'N/A'
        }
    
    def _check_status_mapping(self):
        total = self._run_query("SELECT COUNT(*) FROM adp_hcm.hcm_employee")
        mapped = self._run_query("SELECT COUNT(*) FROM adp_hcm.hcm_employee WHERE worker_status_cd IS NOT NULL AND worker_status_cd != ''")
        unmapped = self._run_query("SELECT COUNT(*) FROM adp_hcm.hcm_employee WHERE worker_status_cd IS NULL OR worker_status_cd = ''")
        status_dist = self._run_query("""
            SELECT worker_status_cd, COUNT(*) FROM adp_hcm.hcm_employee 
            GROUP BY worker_status_cd
        """)
        status = 'PASS' if unmapped == 0 else 'WARN'
        return {
            'name': 'status_mapping',
            'description': 'Worker status code mapping check',
            'total_employees': total,
            'mapped_count': mapped,
            'unmapped_count': unmapped,
            'status_distribution': str(status_dist) if status_dist else '{}',
            'status': status,
            'threshold': '0 unmapped'
        }

if __name__ == '__main__':
    validator = ValidationSuite()
    report = validator.run_all()
    
    import os
    os.makedirs('output', exist_ok=True)
    report_file = f'output/validation_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f'Report saved: {report_file}')
    for c in report['checks']:
        icon = 'PASS' if c['status'] == 'PASS' else ('WARN' if c['status'] == 'WARN' else ('FAIL' if c['status'] == 'FAIL' else 'INFO'))
        desc = c.get('description', '')
        print(f'{icon}: {c["name"]} - {c["status"]} - {desc}')
    print(f'Summary: {report["summary"]}')
