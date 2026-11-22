
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
