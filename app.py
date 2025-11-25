# تطبيق Flask الرئيسي لنظام الإنذار المبكر
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3
import os
import json
from datetime import datetime, timedelta
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = 'early_warning_system_secret_key_2024'

# مسار قاعدة البيانات
DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'ews.db')

# دالة للحصول على اتصال قاعدة البيانات
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# دالة لتحويل الصف إلى قاموس
def row_to_dict(row):
    return dict(row)

# دالة للتحقق من تسجيل الدخول
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# صفحة تسجيل الدخول
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, password_hash FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='اسم المستخدم أو كلمة المرور غير صحيحة')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# صفحة لوحة التحكم
@app.route('/dashboard')
@login_required
def dashboard():
    # إنشاء إشعارات محاكية تلقائياً
    create_simulated_notifications()
    return render_template('dashboard.html')

# دالة لإنشاء إشعارات محاكية
def create_simulated_notifications():
    conn = get_db()
    cursor = conn.cursor()
    
    # التحقق من وجود إشعارات جديدة في آخر ساعة
    cursor.execute('''
        SELECT COUNT(*) as count FROM notifications
        WHERE created_at > datetime('now', '-1 hour')
    ''')
    recent_count = cursor.fetchone()['count']
    
    if recent_count == 0:
        # إنشاء إشعارات محاكية
        cursor.execute('SELECT id, name FROM companies ORDER BY RANDOM() LIMIT 3')
        companies = cursor.fetchall()
        
        company_name = companies[0][1] if companies else "إحدى الشركات"
        company_id = companies[0][0] if companies else None
        
        notifications = [
            ('تنبيه: مخاطر عالية', f'تم اكتشاف مخاطر عالية في {company_name}', 'danger', 'company', company_id),
            ('تحسن في الأداء', 'تحسن ملحوظ في المؤشرات المالية لعدد من الشركات', 'success', 'financial', None),
            ('تنبيه: انخفاض الربحية', 'انخفاض في نسبة الربحية يتطلب مراجعة فورية', 'warning', 'indicator', None)
        ]
        
        user_id = session.get('user_id', 1)
        for notif in notifications:
            cursor.execute('''
                INSERT INTO notifications (user_id, title, message, notification_type, related_type, related_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, notif[0], notif[1], notif[2], notif[3], notif[4]))
    
    conn.commit()
    conn.close()

# صفحة المؤشرات
@app.route('/indicators')
@login_required
def indicators():
    return render_template('indicators.html')

# صفحة إضافة مؤشر جديد
@app.route('/indicators/new')
@login_required
def new_indicator():
    return render_template('new_indicator.html')

# صفحة التنبيهات
@app.route('/alerts')
@login_required
def alerts():
    return render_template('alerts.html')

# API: الحصول على إحصائيات لوحة التحكم
@app.route('/api/dashboard/stats')
@login_required
def get_dashboard_stats():
    conn = get_db()
    cursor = conn.cursor()
    
    # عدد التنبيهات حسب المستوى
    cursor.execute('''
        SELECT level, COUNT(*) as count 
        FROM alerts 
        WHERE status != 'resolved'
        GROUP BY level
    ''')
    alerts_by_level = {row['level']: row['count'] for row in cursor.fetchall()}
    
    # آخر 10 مؤشرات
    cursor.execute('''
        SELECT i.*, u.username as creator_name
        FROM indicators i
        LEFT JOIN users u ON i.created_by = u.id
        ORDER BY i.created_at DESC
        LIMIT 10
    ''')
    recent_indicators = [row_to_dict(row) for row in cursor.fetchall()]
    
    # آخر 10 تنبيهات
    cursor.execute('''
        SELECT a.*, i.title as indicator_title, u.username as acknowledged_by_name
        FROM alerts a
        LEFT JOIN indicators i ON a.indicator_id = i.id
        LEFT JOIN users u ON a.acknowledged_by = u.id
        ORDER BY a.created_at DESC
        LIMIT 10
    ''')
    recent_alerts = [row_to_dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return jsonify({
        'alerts_by_level': alerts_by_level,
        'recent_indicators': recent_indicators,
        'recent_alerts': recent_alerts
    })

# API: الحصول على جميع المؤشرات
@app.route('/api/indicators')
@login_required
def get_indicators():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT i.*, u.username as creator_name
        FROM indicators i
        LEFT JOIN users u ON i.created_by = u.id
        ORDER BY i.created_at DESC
    ''')
    indicators = [row_to_dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(indicators)

# API: إضافة مؤشر جديد
@app.route('/api/indicators', methods=['POST'])
@login_required
def create_indicator():
    data = request.json
    title = data.get('title')
    description = data.get('description', '')
    source = data.get('source')
    indicator_type = data.get('indicator_type')
    text_value = data.get('text_value')
    numeric_value = data.get('numeric_value')
    date = data.get('date')
    created_by = session['user_id']
    
    if not all([title, source, indicator_type, date]):
        return jsonify({'error': 'الحقول المطلوبة مفقودة'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO indicators (title, description, source, indicator_type, text_value, numeric_value, date, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (title, description, source, indicator_type, text_value, numeric_value, date, created_by))
        
        indicator_id = cursor.lastrowid
        
        # تسجيل في audit_log
        cursor.execute('''
            INSERT INTO audit_log (user_id, action, table_name, record_id, details)
            VALUES (?, ?, ?, ?, ?)
        ''', (created_by, 'CREATE', 'indicators', indicator_id, f'تم إنشاء مؤشر جديد: {title}'))
        
        # كشف الشذوذ
        check_anomalies(cursor, indicator_id, indicator_type, numeric_value, source, date)
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'id': indicator_id})
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': str(e)}), 500

# دالة كشف الشذوذ
def check_anomalies(cursor, indicator_id, indicator_type, numeric_value, source, date):
    # الحصول على قواعد كشف الشذوذ
    cursor.execute('SELECT key_name, value FROM settings')
    settings = {row['key_name']: row['value'] for row in cursor.fetchall()}
    
    if settings.get('anomaly_check_enabled', 'true') != 'true':
        return
    
    alerts_created = []
    
    # قاعدة 1: إذا كان المؤشر رقمي وكانت القيمة تمثل انخفاض أو ارتفاع >= 20%
    if indicator_type == 'numeric' and numeric_value is not None:
        threshold = float(settings.get('anomaly_threshold_percentage', '20'))
        if abs(numeric_value) >= threshold:
            level = 'high'
            message = f'انحراف كبير في المؤشر: {abs(numeric_value):.2f}% (الحد: {threshold}%)'
            cursor.execute('''
                INSERT INTO alerts (indicator_id, level, message)
                VALUES (?, ?, ?)
            ''', (indicator_id, level, message))
            alerts_created.append((level, message))
    
    # قاعدة 2: انحراف عن المتوسط التاريخي
    if indicator_type == 'numeric' and numeric_value is not None:
        cursor.execute('''
            SELECT AVG(numeric_value) as avg_value, 
                   COUNT(*) as count
            FROM indicators 
            WHERE indicator_type = 'numeric' 
            AND numeric_value IS NOT NULL
            AND id != ?
        ''', (indicator_id,))
        result = cursor.fetchone()
        
        if result and result['count'] > 0:
            avg_value = result['avg_value']
            if avg_value != 0:
                deviation_threshold = float(settings.get('anomaly_threshold_deviation', '2.5'))
                deviation = abs((numeric_value - avg_value) / avg_value) * 100
                
                if deviation > deviation_threshold * 10:
                    level = 'medium'
                    message = f'انحراف عن المتوسط التاريخي: {deviation:.2f}%'
                    cursor.execute('''
                        INSERT INTO alerts (indicator_id, level, message)
                        VALUES (?, ?, ?)
                    ''', (indicator_id, level, message))
                    alerts_created.append((level, message))
    
    # قاعدة 3: أكثر من 5 مؤشرات من نفس المصدر خلال 24 ساعة
    date_obj = datetime.strptime(date, '%Y-%m-%d')
    start_date = date_obj - timedelta(days=1)
    
    cursor.execute('''
        SELECT COUNT(*) as count
        FROM indicators
        WHERE source = ? AND date >= ?
    ''', (source, start_date.strftime('%Y-%m-%d')))
    
    count_result = cursor.fetchone()
    max_count = int(settings.get('max_indicators_per_source_24h', '5'))
    
    if count_result and count_result['count'] > max_count:
        level = 'medium'
        message = f'عدد كبير من المؤشرات من المصدر نفسه خلال 24 ساعة: {count_result["count"]}'
        cursor.execute('''
            INSERT INTO alerts (indicator_id, level, message)
            VALUES (?, ?, ?)
        ''', (indicator_id, level, message))
        alerts_created.append((level, message))

# API: الحصول على جميع التنبيهات
@app.route('/api/alerts')
@login_required
def get_alerts():
    status_filter = request.args.get('status', 'all')
    conn = get_db()
    cursor = conn.cursor()
    
    if status_filter == 'all':
        cursor.execute('''
            SELECT a.*, i.title as indicator_title, u.username as acknowledged_by_name
            FROM alerts a
            LEFT JOIN indicators i ON a.indicator_id = i.id
            LEFT JOIN users u ON a.acknowledged_by = u.id
            ORDER BY a.created_at DESC
        ''')
    else:
        cursor.execute('''
            SELECT a.*, i.title as indicator_title, u.username as acknowledged_by_name
            FROM alerts a
            LEFT JOIN indicators i ON a.indicator_id = i.id
            LEFT JOIN users u ON a.acknowledged_by = u.id
            WHERE a.status = ?
            ORDER BY a.created_at DESC
        ''', (status_filter,))
    
    alerts = [row_to_dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(alerts)

# API: تحديث حالة التنبيه
@app.route('/api/alerts/<int:alert_id>', methods=['PUT'])
@login_required
def update_alert(alert_id):
    data = request.json
    new_status = data.get('status')
    
    if new_status not in ['acknowledged', 'resolved']:
        return jsonify({'error': 'حالة غير صحيحة'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        if new_status == 'acknowledged':
            cursor.execute('''
                UPDATE alerts 
                SET status = ?, acknowledged_by = ?, acknowledged_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (new_status, session['user_id'], alert_id))
        else:
            cursor.execute('''
                UPDATE alerts 
                SET status = ?
                WHERE id = ?
            ''', (new_status, alert_id))
        
        # تسجيل في audit_log
        cursor.execute('''
            INSERT INTO audit_log (user_id, action, table_name, record_id, details)
            VALUES (?, ?, ?, ?, ?)
        ''', (session['user_id'], 'UPDATE', 'alerts', alert_id, f'تم تحديث حالة التنبيه إلى: {new_status}'))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': str(e)}), 500

# API: الحصول على الإعدادات
@app.route('/api/settings')
@login_required
def get_settings():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM settings')
    settings = [row_to_dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(settings)

# API: تحديث الإعدادات
@app.route('/api/settings/<key_name>', methods=['PUT'])
@login_required
def update_setting(key_name):
    data = request.json
    new_value = data.get('value')
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE settings 
            SET value = ?, updated_at = CURRENT_TIMESTAMP
            WHERE key_name = ?
        ''', (new_value, key_name))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': str(e)}), 500

# صفحة حول المشروع
@app.route('/about')
@login_required
def about():
    return render_template('about.html')

# صفحة السياسات والشروط
@app.route('/policies')
@login_required
def policies():
    return render_template('policies.html')

# صفحة الشركات
@app.route('/companies')
@login_required
def companies():
    return render_template('companies.html')

# صفحة إدارة المخاطر
@app.route('/risk_management')
@login_required
def risk_management():
    return render_template('risk_management.html')

# صفحة التقارير
@app.route('/reports')
@login_required
def reports():
    return render_template('reports.html')

# API: الحصول على جميع الشركات
@app.route('/api/companies')
@login_required
def get_companies():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM companies ORDER BY name')
    companies = [row_to_dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(companies)

# API: الحصول على شركة محددة
@app.route('/api/companies/<int:company_id>')
@login_required
def get_company(company_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM companies WHERE id = ?', (company_id,))
    company = cursor.fetchone()
    if company:
        company_dict = row_to_dict(company)
        cursor.execute('SELECT * FROM strategies WHERE company_id = ?', (company_id,))
        company_dict['strategies'] = [row_to_dict(row) for row in cursor.fetchall()]
        cursor.execute('SELECT * FROM risks WHERE company_id = ?', (company_id,))
        company_dict['risks'] = [row_to_dict(row) for row in cursor.fetchall()]
        cursor.execute('SELECT * FROM financial_analyses WHERE company_id = ? ORDER BY analysis_date DESC LIMIT 12', (company_id,))
        company_dict['financial_analyses'] = [row_to_dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(company_dict)
    conn.close()
    return jsonify({'error': 'الشركة غير موجودة'}), 404

# API: الحصول على المخاطر
@app.route('/api/risks')
@login_required
def get_risks():
    company_id = request.args.get('company_id')
    conn = get_db()
    cursor = conn.cursor()
    
    if company_id:
        cursor.execute('''
            SELECT r.*, c.name as company_name
            FROM risks r
            LEFT JOIN companies c ON r.company_id = c.id
            WHERE r.company_id = ?
            ORDER BY r.risk_level DESC, r.created_at DESC
        ''', (company_id,))
    else:
        cursor.execute('''
            SELECT r.*, c.name as company_name
            FROM risks r
            LEFT JOIN companies c ON r.company_id = c.id
            ORDER BY r.risk_level DESC, r.created_at DESC
        ''')
    
    risks = [row_to_dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(risks)

# API: تحديث حالة المخاطرة
@app.route('/api/risks/<int:risk_id>', methods=['PUT'])
@login_required
def update_risk(risk_id):
    data = request.json
    new_status = data.get('status')
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE risks 
            SET status = ?
            WHERE id = ?
        ''', (new_status, risk_id))
        
        cursor.execute('''
            INSERT INTO audit_log (user_id, action, table_name, record_id, details)
            VALUES (?, ?, ?, ?, ?)
        ''', (session['user_id'], 'UPDATE', 'risks', risk_id, f'تم تحديث حالة المخاطرة إلى: {new_status}'))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': str(e)}), 500

# API: الحصول على الإشعارات
@app.route('/api/notifications')
@login_required
def get_notifications():
    unread_only = request.args.get('unread_only', 'false') == 'true'
    conn = get_db()
    cursor = conn.cursor()
    
    if unread_only:
        cursor.execute('''
            SELECT * FROM notifications
            WHERE user_id = ? AND is_read = 0
            ORDER BY created_at DESC
            LIMIT 10
        ''', (session['user_id'],))
    else:
        cursor.execute('''
            SELECT * FROM notifications
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 50
        ''', (session['user_id'],))
    
    notifications = [row_to_dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(notifications)

# API: تحديث حالة الإشعار
@app.route('/api/notifications/<int:notification_id>', methods=['PUT'])
@login_required
def update_notification(notification_id):
    data = request.json
    is_read = data.get('is_read', 1)
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE notifications 
            SET is_read = ?
            WHERE id = ? AND user_id = ?
        ''', (is_read, notification_id, session['user_id']))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': str(e)}), 500

# API: إنشاء تقرير
@app.route('/api/reports/generate', methods=['POST'])
@login_required
def generate_report():
    data = request.json
    report_type = data.get('report_type', 'comprehensive')
    format_type = data.get('format', 'json')
    company_id = data.get('company_id')
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        report_data = {}
        
        if report_type == 'comprehensive' or report_type == 'risk':
            if company_id:
                cursor.execute('SELECT * FROM risks WHERE company_id = ?', (company_id,))
            else:
                cursor.execute('SELECT r.*, c.name as company_name FROM risks r LEFT JOIN companies c ON r.company_id = c.id')
            report_data['risks'] = [row_to_dict(row) for row in cursor.fetchall()]
        
        if report_type == 'comprehensive' or report_type == 'financial':
            if company_id:
                cursor.execute('SELECT * FROM financial_analyses WHERE company_id = ? ORDER BY analysis_date DESC', (company_id,))
            else:
                cursor.execute('SELECT f.*, c.name as company_name FROM financial_analyses f LEFT JOIN companies c ON f.company_id = c.id ORDER BY f.analysis_date DESC')
            report_data['financial_analyses'] = [row_to_dict(row) for row in cursor.fetchall()]
        
        if company_id:
            cursor.execute('SELECT * FROM companies WHERE id = ?', (company_id,))
            report_data['company'] = row_to_dict(cursor.fetchone())
        
        report_name = f'report_{report_type}_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        
        reports_dir = os.path.join(os.path.dirname(__file__), 'data', 'reports')
        if not os.path.exists(reports_dir):
            os.makedirs(reports_dir)
        
        if format_type == 'json':
            import json
            file_path = os.path.join(reports_dir, f'{report_name}.json')
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2, default=str)
        
        elif format_type == 'csv':
            import csv
            file_path = os.path.join(reports_dir, f'{report_name}.csv')
            if report_data.get('risks'):
                with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.DictWriter(f, fieldnames=report_data['risks'][0].keys())
                    writer.writeheader()
                    writer.writerows(report_data['risks'])
        
        elif format_type == 'txt':
            file_path = os.path.join(reports_dir, f'{report_name}.txt')
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f'تقرير {report_type}\n')
                f.write('=' * 50 + '\n\n')
                if report_data.get('risks'):
                    f.write('المخاطر:\n')
                    for risk in report_data['risks']:
                        f.write(f"- {risk.get('risk_name', '')}: {risk.get('risk_level', '')}\n")
                if report_data.get('financial_analyses'):
                    f.write('\nالتحليلات المالية:\n')
                    for analysis in report_data['financial_analyses']:
                        f.write(f"- تاريخ: {analysis.get('analysis_date', '')}, الربحية: {analysis.get('profit_margin', 0)}%\n")
        
        cursor.execute('''
            INSERT INTO reports (report_name, report_type, format, generated_by, file_path, parameters)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (report_name, report_type, format_type, session['user_id'], file_path, json.dumps(data)))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'file_path': file_path,
            'report_name': report_name
        })
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': str(e)}), 500

# API: الحصول على التقارير السابقة
@app.route('/api/reports')
@login_required
def get_reports():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT r.*, u.username as generated_by_name
        FROM reports r
        LEFT JOIN users u ON r.generated_by = u.id
        ORDER BY r.created_at DESC
        LIMIT 50
    ''')
    reports = [row_to_dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(reports)

# Route لتحميل ملفات التقارير
@app.route('/data/reports/<filename>')
@login_required
def download_report(filename):
    from flask import send_from_directory
    reports_dir = os.path.join(os.path.dirname(__file__), 'data', 'reports')
    return send_from_directory(reports_dir, filename)

# API: الحصول على إحصائيات شاملة
@app.route('/api/dashboard/comprehensive')
@login_required
def get_comprehensive_stats():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) as count FROM companies')
    total_companies = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM risks WHERE status = "active"')
    active_risks = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM risks WHERE risk_level = "high" OR risk_level = "critical"')
    high_risks = cursor.fetchone()['count']
    
    cursor.execute('SELECT AVG(profit_margin) as avg FROM financial_analyses')
    avg_profit = cursor.fetchone()['avg'] or 0
    
    cursor.execute('SELECT COUNT(*) as count FROM alerts WHERE status = "new"')
    new_alerts = cursor.fetchone()['count']
    
    conn.close()
    
    return jsonify({
        'total_companies': total_companies,
        'active_risks': active_risks,
        'high_risks': high_risks,
        'avg_profit_margin': round(avg_profit, 2),
        'new_alerts': new_alerts
    })

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)

