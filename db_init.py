# تهيئة قاعدة البيانات وإنشاء الجداول
import sqlite3
import os
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import random

# إنشاء مجلد data إذا لم يكن موجوداً
db_dir = os.path.join(os.path.dirname(__file__), 'data')
if not os.path.exists(db_dir):
    os.makedirs(db_dir)

db_path = os.path.join(db_dir, 'ews.db')

# الاتصال بقاعدة البيانات
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# جدول المستخدمين
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

# جدول المؤشرات
cursor.execute('''
CREATE TABLE IF NOT EXISTS indicators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    source TEXT NOT NULL,
    indicator_type TEXT NOT NULL CHECK(indicator_type IN ('text', 'numeric')),
    text_value TEXT,
    numeric_value REAL,
    date DATE NOT NULL,
    created_by INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id)
)
''')

# جدول التنبيهات
cursor.execute('''
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    indicator_id INTEGER NOT NULL,
    level TEXT NOT NULL CHECK(level IN ('low', 'medium', 'high')),
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'new' CHECK(status IN ('new', 'acknowledged', 'resolved')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    acknowledged_by INTEGER,
    acknowledged_at TIMESTAMP,
    FOREIGN KEY (indicator_id) REFERENCES indicators(id),
    FOREIGN KEY (acknowledged_by) REFERENCES users(id)
)
''')

# جدول سجل التدقيق
cursor.execute('''
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    table_name TEXT NOT NULL,
    record_id INTEGER,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
)
''')

# جدول الإعدادات
cursor.execute('''
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key_name TEXT UNIQUE NOT NULL,
    value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

# جدول الشركات
cursor.execute('''
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    sector TEXT NOT NULL,
    industry TEXT,
    description TEXT,
    risk_level TEXT CHECK(risk_level IN ('low', 'medium', 'high')),
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'inactive', 'monitoring')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

# جدول الاستراتيجيات
cursor.execute('''
CREATE TABLE IF NOT EXISTS strategies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    strategy_type TEXT CHECK(strategy_type IN ('financial', 'operational', 'market', 'compliance')),
    target_metrics TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id)
)
''')

# جدول المخاطر
cursor.execute('''
CREATE TABLE IF NOT EXISTS risks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    risk_name TEXT NOT NULL,
    risk_category TEXT CHECK(risk_category IN ('financial', 'operational', 'strategic', 'compliance', 'reputational')),
    risk_level TEXT CHECK(risk_level IN ('low', 'medium', 'high', 'critical')),
    probability REAL,
    impact REAL,
    mitigation_plan TEXT,
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'mitigated', 'resolved')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id)
)
''')

# جدول التحليلات المالية
cursor.execute('''
CREATE TABLE IF NOT EXISTS financial_analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    analysis_date DATE NOT NULL,
    revenue REAL,
    profit_margin REAL,
    debt_ratio REAL,
    liquidity_ratio REAL,
    roe REAL,
    roa REAL,
    current_ratio REAL,
    quick_ratio REAL,
    analysis_summary TEXT,
    risk_assessment TEXT,
    recommendations TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id)
)
''')

# جدول الإشعارات
cursor.execute('''
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    notification_type TEXT CHECK(notification_type IN ('info', 'warning', 'danger', 'success')),
    related_type TEXT,
    related_id INTEGER,
    is_read INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
)
''')

# جدول التقارير
cursor.execute('''
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_name TEXT NOT NULL,
    report_type TEXT CHECK(report_type IN ('risk', 'financial', 'compliance', 'comprehensive')),
    format TEXT CHECK(format IN ('json', 'txt', 'csv', 'html')),
    generated_by INTEGER,
    file_path TEXT,
    parameters TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (generated_by) REFERENCES users(id)
)
''')

# إدخال المستخدم الإداري الافتراضي
admin_password_hash = generate_password_hash('admin123')
cursor.execute('''
INSERT OR IGNORE INTO users (username, password_hash) 
VALUES (?, ?)
''', ('admin', admin_password_hash))

# إدخال قواعد كشف الشذوذ في جدول settings
default_rules = [
    ('anomaly_threshold_percentage', '20', 'نسبة الانخفاض أو الارتفاع المئوية لإطلاق تنبيه عالي'),
    ('anomaly_threshold_deviation', '2.5', 'عدد الانحرافات المعيارية عن المتوسط لإطلاق تنبيه متوسط'),
    ('max_indicators_per_source_24h', '5', 'الحد الأقصى لعدد المؤشرات من نفس المصدر خلال 24 ساعة'),
    ('anomaly_check_enabled', 'true', 'تفعيل أو تعطيل كشف الشذوذ')
]

for rule_key, rule_value, rule_desc in default_rules:
    cursor.execute('''
    INSERT OR IGNORE INTO settings (key_name, value, description)
    VALUES (?, ?, ?)
    ''', (rule_key, rule_value, rule_desc))

# إضافة بيانات افتراضية للشركات
companies_data = [
    ('شركة التقنية المتقدمة', 'تقنية المعلومات', 'برمجيات', 'شركة رائدة في تطوير البرمجيات والحلول التقنية', 'medium'),
    ('مؤسسة المال والاستثمار', 'مالية', 'استثمار', 'مؤسسة مالية متخصصة في إدارة الاستثمارات والأصول', 'high'),
    ('شركة الصناعات البترولية', 'طاقة', 'بترول وغاز', 'شركة تعمل في مجال استكشاف وإنتاج النفط والغاز', 'high'),
    ('مجموعة الخدمات الطبية', 'صحة', 'رعاية صحية', 'مجموعة مستشفيات ومراكز طبية متخصصة', 'medium'),
    ('شركة البناء والتطوير', 'عقارات', 'بناء وتشييد', 'شركة متخصصة في البناء والتطوير العقاري', 'medium'),
    ('مؤسسة التجارة الإلكترونية', 'تجارة', 'تجارة إلكترونية', 'منصة تجارة إلكترونية رائدة في المنطقة', 'low'),
    ('بنك الخليج المالي', 'مالية', 'خدمات مصرفية', 'بنك تجاري يقدم خدمات مصرفية شاملة', 'high'),
    ('شركة النقل واللوجستيات', 'نقل', 'لوجستيات', 'شركة متخصصة في خدمات النقل والتوزيع', 'medium')
]

for company in companies_data:
    cursor.execute('''
    INSERT OR IGNORE INTO companies (name, sector, industry, description, risk_level)
    VALUES (?, ?, ?, ?, ?)
    ''', company)

# الحصول على معرفات الشركات
cursor.execute('SELECT id FROM companies')
company_ids = [row[0] for row in cursor.fetchall()]

# إضافة استراتيجيات افتراضية
strategies_data = []
for company_id in company_ids:
    strategies_data.extend([
        (company_id, 'استراتيجية النمو المالي', 'زيادة الإيرادات بنسبة 15% سنوياً', 'financial', '{"revenue_growth": 15, "profit_margin": 20}'),
        (company_id, 'استراتيجية إدارة المخاطر', 'تقليل المخاطر التشغيلية بنسبة 30%', 'operational', '{"risk_reduction": 30}'),
        (company_id, 'استراتيجية الامتثال', 'ضمان الامتثال الكامل للمعايير واللوائح', 'compliance', '{"compliance_rate": 100}'),
        (company_id, 'استراتيجية السوق', 'زيادة الحصة السوقية بنسبة 10%', 'market', '{"market_share": 10}')
    ])

for strategy in strategies_data:
    cursor.execute('''
    INSERT OR IGNORE INTO strategies (company_id, name, description, strategy_type, target_metrics)
    VALUES (?, ?, ?, ?, ?)
    ''', strategy)

# إضافة مخاطر افتراضية
risks_data = []
risk_categories = ['financial', 'operational', 'strategic', 'compliance', 'reputational']
risk_levels = ['low', 'medium', 'high', 'critical']
risk_names = [
    'مخاطر السيولة المالية',
    'مخاطر الائتمان',
    'مخاطر السوق',
    'مخاطر التشغيل',
    'مخاطر التقنية',
    'مخاطر الامتثال',
    'مخاطر السمعة',
    'مخاطر الاستراتيجية',
    'مخاطر الكوارث الطبيعية',
    'مخاطر الأمن السيبراني'
]

for company_id in company_ids:
    for i in range(random.randint(3, 6)):
        risk_name = random.choice(risk_names)
        category = random.choice(risk_categories)
        level = random.choice(risk_levels)
        probability = round(random.uniform(0.1, 0.9), 2)
        impact = round(random.uniform(0.1, 1.0), 2)
        mitigation = f'خطة تخفيف للمخاطر: {risk_name}'
        
        risks_data.append((
            company_id, risk_name, category, level, probability, impact, mitigation, 'active'
        ))

for risk in risks_data:
    cursor.execute('''
    INSERT OR IGNORE INTO risks (company_id, risk_name, risk_category, risk_level, probability, impact, mitigation_plan, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', risk)

# إضافة تحليلات مالية افتراضية
financial_analyses_data = []
for company_id in company_ids:
    for i in range(12):
        analysis_date = (datetime.now() - timedelta(days=30*i)).strftime('%Y-%m-%d')
        revenue = round(random.uniform(1000000, 50000000), 2)
        profit_margin = round(random.uniform(5, 35), 2)
        debt_ratio = round(random.uniform(0.2, 0.8), 2)
        liquidity_ratio = round(random.uniform(1.0, 3.0), 2)
        roe = round(random.uniform(5, 25), 2)
        roa = round(random.uniform(3, 15), 2)
        current_ratio = round(random.uniform(1.0, 2.5), 2)
        quick_ratio = round(random.uniform(0.8, 2.0), 2)
        
        risk_assessment = 'منخفض' if profit_margin > 20 and debt_ratio < 0.5 else 'متوسط' if profit_margin > 10 else 'عالي'
        recommendations = 'تحسين الأداء المالي' if profit_margin < 15 else 'الحفاظ على الأداء الحالي'
        
        financial_analyses_data.append((
            company_id, analysis_date, revenue, profit_margin, debt_ratio, liquidity_ratio,
            roe, roa, current_ratio, quick_ratio,
            f'تحليل مالي شامل للشركة بتاريخ {analysis_date}',
            risk_assessment,
            recommendations
        ))

for analysis in financial_analyses_data:
    cursor.execute('''
    INSERT OR IGNORE INTO financial_analyses 
    (company_id, analysis_date, revenue, profit_margin, debt_ratio, liquidity_ratio, roe, roa, current_ratio, quick_ratio, analysis_summary, risk_assessment, recommendations)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', analysis)

# إضافة مؤشرات افتراضية مرتبطة بالشركات
cursor.execute('SELECT id FROM users WHERE username = ?', ('admin',))
admin_user_id = cursor.fetchone()[0]

indicators_data = []
indicator_titles = [
    'نسبة الدين إلى حقوق الملكية',
    'نسبة السيولة الحالية',
    'نسبة الربحية',
    'نسبة النمو في الإيرادات',
    'مؤشر الأداء التشغيلي',
    'مؤشر رضا العملاء',
    'مؤشر جودة المنتج',
    'مؤشر كفاءة الموظفين',
    'مؤشر الامتثال التنظيمي',
    'مؤشر الأمن السيبراني'
]

for idx, company_id in enumerate(company_ids):
    company_name = companies_data[idx][0] if idx < len(companies_data) else f'شركة {company_id}'
    for i in range(random.randint(15, 25)):
        days_ago = random.randint(0, 90)
        indicator_date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
        title = random.choice(indicator_titles)
        indicator_type = 'numeric'
        numeric_value = round(random.uniform(-50, 50), 2)
        
        indicators_data.append((
            title,
            f'مؤشر {title} لـ {company_name}',
            company_name,
            indicator_type,
            None,
            numeric_value,
            indicator_date,
            admin_user_id
        ))

for indicator in indicators_data:
    cursor.execute('''
    INSERT OR IGNORE INTO indicators (title, description, source, indicator_type, text_value, numeric_value, date, created_by)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', indicator)

# إضافة تنبيهات افتراضية
cursor.execute('SELECT id FROM indicators LIMIT 50')
indicator_ids = [row[0] for row in cursor.fetchall()]

alerts_data = []
alert_messages = [
    'انخفاض حاد في نسبة الربحية',
    'ارتفاع في نسبة الدين',
    'تراجع في مؤشر رضا العملاء',
    'انخفاض في مؤشر الأداء التشغيلي',
    'مخاطر امتثال محتملة',
    'تحسن ملحوظ في الأداء المالي',
    'زيادة في مؤشر الكفاءة',
    'تحسن في مؤشر الأمن'
]

for indicator_id in indicator_ids[:30]:
    level = random.choice(['low', 'medium', 'high'])
    message = random.choice(alert_messages)
    status = random.choice(['new', 'acknowledged', 'resolved'])
    
    alerts_data.append((
        indicator_id, level, message, status
    ))

for alert in alerts_data:
    cursor.execute('''
    INSERT OR IGNORE INTO alerts (indicator_id, level, message, status)
    VALUES (?, ?, ?, ?)
    ''', alert)

# إضافة إشعارات افتراضية
notifications_data = [
    (admin_user_id, 'تنبيه: مخاطر عالية', 'تم اكتشاف مخاطر عالية في شركة التقنية المتقدمة', 'danger', 'company', 1),
    (admin_user_id, 'تحسن في الأداء', 'تحسن ملحوظ في مؤشرات الأداء المالي', 'success', 'financial', 1),
    (admin_user_id, 'تنبيه: انخفاض الربحية', 'انخفاض في نسبة الربحية يتطلب مراجعة', 'warning', 'indicator', 1),
    (admin_user_id, 'تقرير جاهز', 'تم إنشاء تقرير المخاطر الشامل', 'info', 'report', None)
]

for notification in notifications_data:
    cursor.execute('''
    INSERT OR IGNORE INTO notifications (user_id, title, message, notification_type, related_type, related_id)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', notification)

conn.commit()
conn.close()

print('تم إنشاء قاعدة البيانات والجداول بنجاح.')
print('تم إضافة بيانات افتراضية:')
print(f'- {len(companies_data)} شركة')
print(f'- {len(strategies_data)} استراتيجية')
print(f'- {len(risks_data)} مخاطرة')
print(f'- {len(financial_analyses_data)} تحليل مالي')
print(f'- {len(indicators_data)} مؤشر')
print(f'- {len(alerts_data)} تنبيه')
print('المستخدم الافتراضي: admin / admin123')

