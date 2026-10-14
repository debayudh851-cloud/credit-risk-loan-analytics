"""Validated CSV ingestion with real database constraints and atomic replacement."""
import io
import json
import shutil
import sqlite3
import numpy as np
from pathlib import Path
import pandas as pd
from .config import ROOT, DATA, OUT, prepare

TABLES = {'customers': 'customer_id', 'credit_history': 'credit_id',
          'loan_applications': 'application_id', 'transactions': 'transaction_id'}
FILES = {'customers': 'customers (1).csv', 'credit_history': 'credit_history.csv',
         'loan_applications': 'loan_applications.csv', 'transactions': 'transactions.csv'}

def native(value):
    if pd.isna(value):
        return None
    return value.item() if isinstance(value,np.generic) else value

def read_raw():
    prepare()
    frames = {}
    for table, original in FILES.items():
        canonical = DATA / f'{table}.csv'
        if not canonical.exists():
            if not (ROOT / original).exists():
                raise FileNotFoundError(f'Provide datasets/{table}.csv or {original}')
            shutil.copy2(ROOT / original, canonical)
        frames[table] = pd.read_csv(canonical)
    return frames

def validate(frames):
    report = {}
    parent = set(frames['customers'].customer_id)
    for table, key in TABLES.items():
        d = frames[table]
        if d[key].isna().any() or d[key].duplicated().any():
            raise ValueError(f'{table}: invalid primary key')
        orphans = 0 if table == 'customers' else int((~d.customer_id.isin(parent)).sum())
        if orphans:
            raise ValueError(f'{table}: {orphans} orphan foreign keys')
        for col in [c for c in d if c.endswith('_date') or c in ['date_of_birth', 'customer_since']]:
            pd.to_datetime(d[col], errors='raise')
        report[table] = {'rows': len(d), 'orphans': orphans, 'missing': d.isna().sum().to_dict()}
    c = frames['credit_history']
    if c.customer_id.duplicated().any():
        raise ValueError('Bureau records must be one per customer')
    l = frames['loan_applications']
    if not (((l.disbursed_flag == 1) & l.loan_default.isin([0, 1])) |
            ((l.disbursed_flag == 0) & l.loan_default.isna())).all():
        raise ValueError('Target observed exactly on disbursed loans')
    report['timing'] = {'bureau_after_application_count': int((pd.to_datetime(l.application_date) < pd.to_datetime(c.as_of_date).min()).sum()),
                        'bureau_snapshot_dates': sorted(c.as_of_date.unique().tolist()),
                        'transaction_start': frames['transactions'].transaction_date.min(),
                        'transaction_end': frames['transactions'].transaction_date.max()}
    report['remediation'] = {'duplicate_contact_emails_set_to_null_on_load': int(frames['customers'].email.duplicated().sum())}
    joined = l.merge(frames['customers'][['customer_id','customer_since']], on='customer_id', validate='many_to_one')
    report['timing']['relationship_starts_after_application_count'] = int((joined.application_date < joined.customer_since).sum())
    return report

def connect(url=None):
    if url:
        import psycopg2
        return psycopg2.connect(url)
    connection = sqlite3.connect(OUT / 'credit_risk.sqlite')
    connection.execute('PRAGMA foreign_keys=ON')
    return connection

def load(frames, url=None, write_report=True):
    report = validate(frames)
    conn = connect(url)
    schema = (ROOT / 'sql' / 'schema.sql').read_text(encoding='utf-8')
    try:
        with conn:
            cur = conn.cursor()
            for statement in schema.split(';'):
                if statement.strip():
                    cur.execute(statement)
            for table in reversed(list(TABLES)):
                cur.execute(f'DELETE FROM {table}')
            for table in TABLES:
                d = frames[table].copy()
                if table == 'customers':
                    # Preserve raw CSV; null repeated optional contacts, enforcing UNIQUE.
                    d.loc[d.email.duplicated(), 'email'] = None
                if table == 'loan_applications':
                    d['loan_default'] = d.loan_default.astype('Int64')
                if url:
                    stream = io.StringIO()
                    d.to_csv(stream, index=False, header=False, na_rep='\\N')
                    stream.seek(0)
                    columns = ','.join(d.columns)
                    cur.copy_expert(f"COPY {table} ({columns}) FROM STDIN WITH (FORMAT CSV, NULL '\\N')", stream)
                else:
                    values = [tuple(native(v) for v in row) for row in d.itertuples(index=False, name=None)]
                    cur.executemany(f"INSERT INTO {table} ({','.join(d.columns)}) VALUES ({','.join('?' for _ in d.columns)})", values)
            if not url:
                assert not conn.execute('PRAGMA foreign_key_check').fetchall()
        report['engine'] = 'PostgreSQL' if url else 'SQLite portable fallback'
        if write_report:
            (OUT / 'data_quality.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    finally:
        conn.close()
    return report

def write_scores(applications, customers, url=None):
    conn = connect(url)
    try:
        with conn:
            cur = conn.cursor()
            cur.execute('DELETE FROM scored_applications')
            cur.execute('DELETE FROM scored_customers')
            for table, df in [('scored_applications', applications), ('scored_customers', customers)]:
                columns = list(df.columns)
                marker = '%s' if url else '?'
                values = [tuple(native(v) for v in row) for row in df.itertuples(index=False, name=None)]
                cur.executemany(f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join([marker]*len(columns))})", values)
    finally:
        conn.close()
