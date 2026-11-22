# Extract from PostgreSQL legacy_hr schema
from src.utils.db import get_pg_conn, put_pg_conn
import pandas as pd

def extract_employees():
    '''Get all employees as DataFrame'''
    conn = get_pg_conn()
    try:
        return pd.read_sql('SELECT * FROM legacy_hr.employees ORDER BY emp_id', conn)
    finally:
        put_pg_conn(conn)

def extract_departments():
    conn = get_pg_conn()
    try:
        return pd.read_sql('SELECT * FROM legacy_hr.departments', conn)
    finally:
        put_pg_conn(conn)

def extract_jobs():
    conn = get_pg_conn()
    try:
        return pd.read_sql('SELECT * FROM legacy_hr.jobs', conn)
    finally:
        put_pg_conn(conn)

def extract_all():
    '''Extract everything at once'''
    conn = get_pg_conn()
    try:
        return {
            'employees': pd.read_sql('SELECT * FROM legacy_hr.employees', conn),
            'departments': pd.read_sql('SELECT * FROM legacy_hr.departments', conn),
            'jobs': pd.read_sql('SELECT * FROM legacy_hr.jobs', conn),
        }
    finally:
        put_pg_conn(conn)
