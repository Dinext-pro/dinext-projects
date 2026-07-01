// CSS загружается через doctype_css (we-table.css).
// Функция оставлена как no-op для обратной совместимости с вызовами из других скриптов.
function applyWorkEffortsStyles() {
    var old = document.getElementById('work-efforts-styles');
    if (old) old.remove();
}

window.applyWorkEffortsStyles = applyWorkEffortsStyles;

$(document).ready(function() {
    applyWorkEffortsStyles();
});

if (typeof frappe !== 'undefined') {
    frappe.after_ajax(function() {
        applyWorkEffortsStyles();
    });
}
