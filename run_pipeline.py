import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.extract.legacy_extractor import extract_all
from src.transform.mapping_engine import MappingEngine
from src.transform.lookups import lookup_cache
from src.load.hcm_loader import HCMLoader
import json
from datetime import datetime

def main():
    print("=" * 60)
    print("ADP HCM MIGRATION PIPELINE")
    print("=" * 60)
    
    print("\n[1/4] EXTRACTING from legacy systems...")
    data = extract_all()
    print(f"  Employees: {len(data['employees'])}")
    print(f"  Departments: {len(data['departments'])}")
    print(f"  Jobs: {len(data['jobs'])}")
    
    print("\n[2/4] LOADING reference data...")
    loader = HCMLoader()
    loader.load_departments(data['departments'].to_dict('records'))
    loader.load_jobs(data['jobs'].to_dict('records'))
    print(f"  Departments loaded: {loader.stats['inserted']}")
    print(f"  Jobs loaded: {loader.stats['inserted']}")
    
    print("\n[3/4] TRANSFORMING & LOADING employees...")
    engine = MappingEngine()
    loader = HCMLoader()
    
    batch = []
    batch_size = 500
    total = len(data['employees'])
    
    for idx, row in data['employees'].iterrows():
        emp_dict = row.to_dict()
        transformed, errors = engine.transform_employee(emp_dict)
        
        if errors:
            print(f"  WARNING EMP {emp_dict.get('emp_id')}: {errors}")
        
        batch.append(transformed)
        
        if len(batch) >= batch_size:
            loader.load_employees(batch)
            print(f"  Loaded batch: {loader.stats['inserted']}/{total}")
            batch = []
    
    if batch:
        loader.load_employees(batch)
    
    print(f"  Total inserted: {loader.stats['inserted']}")
    print(f"  Total updated: {loader.stats['updated']}")
    print(f"  Transform stats: {engine.stats}")
    
    print("\n[4/4] QUICK VERIFICATION...")
    from src.utils.db import get_pg_conn, put_pg_conn
    
    conn = get_pg_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM adp_hcm.hcm_employee")
            tgt_count = cur.fetchone()[0]
            
            cur.execute("SELECT SUM(annual_salary_usd) FROM adp_hcm.hcm_employee")
            tgt_salary = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM adp_hcm.hcm_employee WHERE ssn_encrypted IS NULL")
            null_ssn = cur.fetchone()[0]
            
            cur.execute("""
                SELECT COUNT(*) FROM (
                    SELECT ssn_encrypted FROM adp_hcm.hcm_employee
                    WHERE ssn_encrypted IS NOT NULL
                    GROUP BY ssn_encrypted HAVING COUNT(*) > 1
                ) t
            """)
            dup_ssn = cur.fetchone()[0]
            
            print(f"  Target employee count: {tgt_count}")
            print(f"  Target total salary (USD): {tgt_salary:,.2f}")
            print(f"  Null SSN count: {null_ssn}")
            print(f"  Duplicate SSN count: {dup_ssn}")
    finally:
        put_pg_conn(conn)
    
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
