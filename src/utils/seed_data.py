import random
import psycopg2
from pymongo import MongoClient
from faker import Faker
from datetime import date, timedelta
import yaml
import os

fake = Faker()
Faker.seed(42)
random.seed(42)

def load_config():
    with open('config/db_config.yaml') as f:
        return yaml.safe_load(f)

def get_pg_conn():
    """Get PostgreSQL connection using environment variables for Docker"""
    cfg = load_config()['postgres']
    host = os.getenv('POSTGRES_HOST', cfg['host'])
    port = int(os.getenv('POSTGRES_PORT', cfg['port']))
    conn_params = {
        'host': host,
        'port': port,
        'database': cfg['database'],
        'user': cfg['user'],
        'password': cfg['password'],
    }
    return psycopg2.connect(**conn_params)

def get_mongo_client():
    """Get MongoDB client using environment variables for Docker"""
    cfg = load_config()['mongodb']
    host = os.getenv('MONGO_HOST', cfg['host'])
    port = int(os.getenv('MONGO_PORT', cfg['port']))
    return MongoClient(host, port)

def seed_departments(cur):
    depts = [
        ('ENG', 'Engineering', None, 'CC100', 'LOC001'),
        ('HR', 'Human Resources', None, 'CC200', 'LOC001'),
        ('FIN', 'Finance', None, 'CC300', 'LOC001'),
        ('SAL', 'Sales', None, 'CC400', 'LOC002'),
        ('MKT', 'Marketing', None, 'CC500', 'LOC002'),
        ('IT', 'Information Technology', None, 'CC600', 'LOC001'),
        ('OPS', 'Operations', None, 'CC700', 'LOC003'),
        ('LGL', 'Legal', None, 'CC800', 'LOC001'),
    ]
    for d in depts:
        cur.execute("""
            INSERT INTO legacy_hr.departments (dept_code, dept_name, parent_dept_code, cost_center, location_code)
            VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING
        """, d)
    return [d[0] for d in depts]

def seed_jobs(cur):
    jobs = [
        ('SE1', 'Software Engineer I', 'L1', 'N', 70000, 90000),
        ('SE2', 'Software Engineer II', 'L2', 'E', 90000, 120000),
        ('SE3', 'Senior Software Engineer', 'L3', 'E', 120000, 160000),
        ('MGR', 'Engineering Manager', 'M1', 'E', 150000, 200000),
        ('HRBP', 'HR Business Partner', 'L2', 'E', 80000, 110000),
        ('FINA', 'Financial Analyst', 'L2', 'E', 75000, 100000),
        ('SALE', 'Sales Executive', 'L2', 'N', 60000, 90000),
        ('OPSA', 'Operations Analyst', 'L1', 'N', 55000, 75000),
    ]
    for j in jobs:
        cur.execute("""
            INSERT INTO legacy_hr.jobs (job_code, job_title, grade_level, flsa_status, min_salary, max_salary)
            VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING
        """, j)
    return [j[0] for j in jobs]

def seed_employees(cur, dept_codes, job_codes, n=5000):
    status_codes = ['AC', 'TM', 'LO', 'RE']
    currencies = ['USD', 'INR']
    genders = ['M', 'F']
    countries = ['US', 'IN']
    states_us = ['CA', 'NY', 'TX', 'FL', 'WA']
    states_in = ['KA', 'MH', 'TG', 'DL', 'TN']
    
    manager_ids = [f'EMP{i:05d}' for i in range(1, 101)]
    
    for i in range(1, n + 1):
        emp_id = f'EMP{i:05d}'
        dept = random.choice(dept_codes)
        job = random.choice(job_codes)
        status = random.choices(status_codes, weights=[0.85, 0.10, 0.03, 0.02])[0]
        currency = random.choices(currencies, weights=[0.7, 0.3])[0]
        country = 'US' if currency == 'USD' else 'IN'
        
        hire_date = fake.date_between(start_date='-10y', end_date='-30d')
        term_date = None
        if status == 'TM':
            term_date = fake.date_between(start_date=hire_date, end_date='today')
            if random.random() < 0.08:
                term_date = None
        
        base_salary = random.randint(50000, 200000)
        if currency == 'INR':
            base_salary = base_salary * 83
        
        email = fake.email() if random.random() > 0.12 else f'invalid-email-{i}'
        ssn = fake.ssn() if random.random() > 0.05 else None
        manager = random.choice(manager_ids) if random.random() > 0.20 else None
        
        cur.execute("""
            INSERT INTO legacy_hr.employees (
                emp_id, first_name, last_name, email, phone, hire_date, termination_date,
                status_code, dept_code, job_code, salary_numeric, currency_cd,
                manager_emp_id, address_line1, city, state, zip_code, country_cd,
                ssn, dob, gender, created_ts, updated_ts
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (
            emp_id,
            fake.first_name(),
            fake.last_name(),
            email,
            fake.phone_number()[:20],
            hire_date,
            term_date,
            status,
            dept,
            job,
            round(base_salary, 2),
            currency,
            manager,
            fake.street_address(),
            fake.city(),
            random.choice(states_us if country == 'US' else states_in),
            fake.zipcode()[:10],
            country,
            ssn,
            fake.date_of_birth(minimum_age=22, maximum_age=65),
            random.choice(genders),
            fake.date_time_this_decade(),
            fake.date_time_this_year(),
        ))

def seed_mongodb():
    client = get_mongo_client()
    db = client['migration_demo']
    coll = db['employee_documents']
    
    doc_types = ['I9', 'W4', 'BENEFITS', 'OFFER_LETTER', 'TAX_FORM']
    statuses = ['VERIFIED', 'PENDING', 'REJECTED']
    
    docs = []
    for i in range(1, 2001):
        docs.append({
            'emp_id': f'EMP{i:05d}',
            'doc_type': random.choice(doc_types),
            'file_name': f'{random.choice(doc_types)}_EMP{i:05d}.pdf',
            'extracted_text': f'Employee document for EMP{i:05d}...',
            'upload_date': fake.date_time_this_year(),
            'status': random.choices(statuses, weights=[0.7, 0.2, 0.1])[0],
            'metadata': {
                'pages': random.randint(1, 5),
                'file_size_kb': random.randint(50, 500),
                'ocr_confidence': round(random.uniform(0.7, 1.0), 2)
            }
        })
    
    if docs:
        coll.insert_many(docs)
    print(f'Inserted {len(docs)} MongoDB documents')
    client.close()

if __name__ == '__main__':
    print('Seeding departments...')
    conn = get_pg_conn()
    cur = conn.cursor()
    
    dept_codes = seed_departments(cur)
    print(f'Seeded {len(dept_codes)} departments')
    
    print('Seeding jobs...')
    job_codes = seed_jobs(cur)
    print(f'Seeded {len(job_codes)} jobs')
    
    print('Seeding employees (5000)...')
    seed_employees(cur, dept_codes, job_codes, 5000)
    
    conn.commit()
    cur.close()
    conn.close()
    
    print('Seeding MongoDB...')
    seed_mongodb()
    
    print('✅ Seed complete!')
