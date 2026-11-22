import os

# 1. FIX LOOKUPS.PY
lookups_code = '''
import json
from src.utils.db import get_pg_conn, put_pg_conn, get_redis

class LookupCache:
    def __init__(self, ttl=3600):
        self.redis = get_redis()
        self.ttl = ttl
    
    def _get_from_redis(self, key):
        cached = self.redis.get(key)
        if cached:
            return json.loads(cached)
        return None
    
    def _set_in_redis(self, key, value):
        self.redis.set(key, json.dumps(value), ex=self.ttl)
    
    def get_dept_mapping(self):
        key = 'lookup:dept_code_to_id'
        cached = self._get_from_redis(key)
        if cached:
            return cached
        
        conn = get_pg_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT SUBSTRING(department_id FROM 3) AS dept_code, department_id FROM adp_hcm.hcm_department")
                mapping = {row[0]: row[1] for row in cur.fetchall()}
        finally:
            put_pg_conn(conn)
        
        self._set_in_redis(key, mapping)
        return mapping
    
    def get_job_mapping(self):
        key = 'lookup:job_code_to_id'
        cached = self._get_from_redis(key)
        if cached:
            return cached
        
        conn = get_pg_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT SUBSTRING(job_id FROM 3) AS job_code, job_id FROM adp_hcm.hcm_job")
                mapping = {row[0]: row[1] for row in cur.fetchall()}
        finally:
            put_pg_conn(conn)
        
        self._set_in_redis(key, mapping)
        return mapping
    
    def get_manager_mapping(self):
        key = 'lookup:emp_id_to_person_id'
        cached = self._get_from_redis(key)
        if cached:
            return cached
        
        conn = get_pg_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT employee_id, person_id FROM adp_hcm.hcm_employee")
                mapping = {row[0]: row[1] for row in cur.fetchall()}
        finally:
            put_pg_conn(conn)
        
        self._set_in_redis(key, mapping)
        return mapping
    
    def get_status_mapping(self):
        key = 'lookup:status_code'
        cached = self._get_from_redis(key)
        if cached:
            return cached
        
        conn = get_pg_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT source_code, target_code FROM adp_hcm.ref_status_mapping")
                mapping = {row[0]: row[1] for row in cur.fetchall()}
        finally:
            put_pg_conn(conn)
        
        self._set_in_redis(key, mapping)
        return mapping
    
    def get_currency_rate(self, from_curr, to_curr):
        key = f'fx:{from_curr}:{to_curr}'
        cached = self._get_from_redis(key)
        if cached:
            return float(cached)
        
        conn = get_pg_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT rate FROM adp_hcm.ref_currency_rate 
                    WHERE from_currency=%s AND to_currency=%s 
                    ORDER BY effective_date DESC LIMIT 1
                """, (from_curr, to_curr))
                row = cur.fetchone()
                rate = float(row[0]) if row else 1.0
        finally:
            put_pg_conn(conn)
        
        self._set_in_redis(key, rate)
        return rate

lookup_cache = LookupCache()
'''

with open('src/transform/lookups.py', 'w', encoding='utf-8') as f:
    f.write(lookups_code)
print("✅ Fixed src/transform/lookups.py")


# 2. FIX HCM_LOADER.PY
loader_code = '''
from src.utils.db import get_pg_conn, put_pg_conn
import psycopg2.extras
import uuid
from datetime import date

class HCMLoader:
    def __init__(self, batch_size=500):
        self.batch_size = batch_size
        self.stats = {'inserted': 0, 'updated': 0, 'errors': 0}
    
    def load_employees(self, employees):
        conn = get_pg_conn()
        try:
            with conn.cursor() as cur:
                for emp in employees:
                    if not emp.get('employee_id'):
                        continue
                    person_id = f'PERS-{uuid.uuid4().hex[:8].upper()}'
                    address_id = self._insert_address(cur, emp)
                    
                    cur.execute("""
                        INSERT INTO adp_hcm.hcm_employee (
                            employee_id, person_id, legal_first_name, legal_last_name,
                            preferred_first_name, work_email, hire_date, termination_date,
                            worker_status_cd, department_id, job_id, compensation_grade,
                            annual_salary_usd, pay_frequency_cd, flsa_status_cd,
                            manager_person_id, home_address_id, work_location_id,
                            ssn_encrypted, date_of_birth, gender_cd,
                            original_hire_date, adjusted_service_date,
                            created_by, created_dt, updated_by, updated_dt
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        ON CONFLICT (employee_id) DO UPDATE SET
                            legal_first_name = EXCLUDED.legal_first_name,
                            legal_last_name = EXCLUDED.legal_last_name,
                            work_email = EXCLUDED.work_email,
                            hire_date = EXCLUDED.hire_date,
                            termination_date = EXCLUDED.termination_date,
                            worker_status_cd = EXCLUDED.worker_status_cd,
                            department_id = EXCLUDED.department_id,
                            job_id = EXCLUDED.job_id,
                            annual_salary_usd = EXCLUDED.annual_salary_usd,
                            manager_person_id = EXCLUDED.manager_person_id,
                            home_address_id = EXCLUDED.home_address_id,
                            ssn_encrypted = EXCLUDED.ssn_encrypted,
                            updated_by = 'MIGRATION',
                            updated_dt = CURRENT_TIMESTAMP
                    """, (
                        emp.get('employee_id'),
                        person_id,
                        emp.get('legal_first_name'),
                        emp.get('legal_last_name'),
                        emp.get('preferred_first_name'),
                        emp.get('work_email'),
                        emp.get('hire_date'),
                        emp.get('termination_date'),
                        emp.get('worker_status_cd'),
                        emp.get('department_id'),
                        emp.get('job_id'),
                        emp.get('compensation_grade'),
                        emp.get('annual_salary_usd'),
                        emp.get('pay_frequency_cd', 'BIWEEKLY'),
                        emp.get('flsa_status_cd'),
                        emp.get('manager_person_id'),
                        address_id,
                        emp.get('work_location_id'),
                        emp.get('ssn_encrypted'),
                        emp.get('date_of_birth'),
                        emp.get('gender_cd'),
                        emp.get('hire_date'),
                        emp.get('hire_date'),
                        'MIGRATION',
                        emp.get('created_dt'),
                        'MIGRATION',
                        emp.get('updated_dt'),
                    ))
                    
                    if cur.rowcount > 0:
                        self.stats['inserted'] += 1
                    else:
                        self.stats['updated'] += 1
                
                conn.commit()
        except Exception as e:
            conn.rollback()
            self.stats['errors'] += 1
            print(f"Error loading employees: {e}")
            raise
        finally:
            put_pg_conn(conn)
    
    def _insert_address(self, cur, emp):
        address_id = f'ADDR-{uuid.uuid4().hex[:8].upper()}'
        cur.execute("""
            INSERT INTO adp_hcm.hcm_address (
                address_id, address_line1, city, state_province,
                postal_code, country_cd, address_type_cd
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (address_id) DO NOTHING
        """, (
            address_id,
            emp.get('address_line1'),
            emp.get('city'),
            emp.get('state_province'),
            emp.get('postal_code'),
            emp.get('country_cd'),
            'HOME'
        ))
        return address_id
    
    def load_departments(self, departments):
        conn = get_pg_conn()
        try:
            with conn.cursor() as cur:
                for dept in departments:
                    cur.execute("""
                        INSERT INTO adp_hcm.hcm_department (
                            department_id, department_name, parent_department_id,
                            cost_center, location_id, effective_start_dt, effective_end_dt
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (department_id) DO UPDATE SET
                            department_name = EXCLUDED.department_name,
                            parent_department_id = EXCLUDED.parent_department_id,
                            cost_center = EXCLUDED.cost_center,
                            location_id = EXCLUDED.location_id
                    """, (
                        f'D-{dept["dept_code"]}',
                        dept['dept_name'],
                        f'D-{dept["parent_dept_code"]}' if dept.get('parent_dept_code') else None,
                        dept.get('cost_center'),
                        f'LOC-{dept["location_code"]}',
                        date.today(),
                        None
                    ))
                    self.stats['inserted'] += 1
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Error loading departments: {e}")
            raise
        finally:
            put_pg_conn(conn)
    
    def load_jobs(self, jobs):
        conn = get_pg_conn()
        try:
            with conn.cursor() as cur:
                for job in jobs:
                    cur.execute("""
                        INSERT INTO adp_hcm.hcm_job (
                            job_id, job_title, job_family, grade_level,
                            flsa_status_cd, min_annual_salary, max_annual_salary
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (job_id) DO UPDATE SET
                            job_title = EXCLUDED.job_title,
                            grade_level = EXCLUDED.grade_level,
                            flsa_status_cd = EXCLUDED.flsa_status_cd,
                            min_annual_salary = EXCLUDED.min_annual_salary,
                            max_annual_salary = EXCLUDED.max_annual_salary
                    """, (
                        f'J-{job["job_code"]}',
                        job['job_title'],
                        'TECH' if 'Engineer' in job['job_title'] else 'CORP',
                        job['grade_level'],
                        job['flsa_status'],
                        job['min_salary'],
                        job['max_salary']
                    ))
                    self.stats['inserted'] += 1
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Error loading jobs: {e}")
            raise
        finally:
            put_pg_conn(conn)
'''

with open('src/load/hcm_loader.py', 'w', encoding='utf-8') as f:
    f.write(loader_code)
print("✅ Fixed src/load/hcm_loader.py")


# 3. RUN THE PIPELINE DIRECTLY
print("\n" + "=" * 60)
print("RUNNING ADP HCM MIGRATION PIPELINE")
print("=" * 60)

import run_pipeline
run_pipeline.main()