"""Per-generation local statistics, without any conversation content."""
import sqlite3
from datetime import datetime, timedelta


class Usage:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('''CREATE TABLE IF NOT EXISTS generations (
            id INTEGER PRIMARY KEY, created TEXT NOT NULL, model TEXT NOT NULL,
            source TEXT NOT NULL, input INTEGER NOT NULL, output INTEGER NOT NULL,
            cached INTEGER NOT NULL, exact INTEGER NOT NULL, seconds REAL NOT NULL,
            state TEXT NOT NULL)''')
        self.db.commit()
        path.chmod(0o600)

    def add(self, event, created=None):
        with self.db:
            self.db.execute('INSERT INTO generations(created,model,source,input,output,cached,exact,seconds,state) VALUES(?,?,?,?,?,?,?,?,?)',
                (created or datetime.now().isoformat(timespec='seconds'), str(event['model'])[:160], event.get('source','chat'),
                 max(0,int(event.get('input',0))), max(0,int(event.get('output',0))), max(0,int(event.get('cached',0))),
                 int(bool(event.get('exact'))), max(0,float(event.get('seconds',0))), event.get('state','complete')))

    def report(self, period='week', now=None):
        now = now or datetime.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start = {'day':today, 'week':today-timedelta(days=6), 'month':today-timedelta(days=29), 'all':datetime.min}[period]
        rows = [dict(r) for r in self.db.execute('SELECT * FROM generations WHERE created>=? AND created<=? ORDER BY created', (start.isoformat(timespec='seconds'),now.isoformat(timespec='seconds')))]
        total = {k:sum(r[k] for r in rows) for k in ['input','output','cached','seconds']}
        total.update(requests=len(rows), failed=sum(r['state']=='failed' for r in rows), cancelled=sum(r['state']=='cancelled' for r in rows), estimated=sum(not r['exact'] and r['state']!='failed' for r in rows))
        by_day, models = {}, {}
        for r in rows:
            day = r['created'][:10]
            by_day[day] = by_day.get(day,0)+r['input']+r['output']
            item = models.setdefault(r['model'], {'model':r['model'],'input':0,'output':0,'requests':0})
            for key in ['input','output']: item[key] += r[key]
            item['requests'] += 1
        chart_days = 1 if period=='day' else 30 if period=='month' else 7
        days = [(today-timedelta(days=n)).date().isoformat() for n in range(chart_days-1,-1,-1)]
        return total, [(d,by_day.get(d,0)) for d in days], sorted(models.values(), key=lambda r: -(r['input']+r['output']))

    def close(self):
        self.db.close()
