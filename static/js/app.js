// ملف JavaScript الرئيسي للتطبيق
// يحتوي على دوال مساعدة عامة

// دالة لعرض رسائل الخطأ
function showError(message) {
    console.error('خطأ:', message);
    alert('حدث خطأ: ' + message);
}

// دالة لعرض رسائل النجاح
function showSuccess(message) {
    console.log('نجاح:', message);
}

// دالة للتحقق من صحة البيانات قبل الإرسال
function validateForm(formData) {
    if (!formData.title || !formData.source || !formData.indicator_type || !formData.date) {
        return { valid: false, error: 'يرجى ملء جميع الحقول المطلوبة' };
    }
    return { valid: true };
}

// دالة لتنسيق التاريخ
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('ar-SA');
}

// دالة لتنسيق الوقت
function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('ar-SA');
}

