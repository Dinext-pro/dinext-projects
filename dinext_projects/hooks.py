app_name = "dinext_projects"
app_title = "Dinext Projects"
app_publisher = "Dinext"
app_description = "Dinext Projects"
app_email = "info@dinext.ru"
app_license = "mit"

fixtures = [
    "Project Payment Scheme",
    "Type Of Leave",    
    "Issue Identification Type",    
    "Workflow State",
    "Workflow Action Master",    
    {
        "doctype": "Role Profile",
        "filters": [
            ["name", "in", 
            [
                "Финансы", 
                "Менеджер Проекта", 
                "Внутренний специалист", 
                "Внешний специалист", 
                "Sales-Менеджер"
            ]]
        ]
    },
    {
        "doctype": "Project Type",
        "filters": [
            ["name", "in", ["Внепроектные работы", "Коммерческий", "Внутренний", "Presale"]]
        ]
    },
    {
        "doctype": "Issue Priority",
        "filters": [
            ["name", "in", ["Низкий", "Средний", "Высокий"]]
        ]
    },
    {
        "doctype": "Custom HTML Block",
        "filters": [
            ["name", "in", ["My Kanban", "Idea Picture", "DiLike Picture", "My Calendar", "Leaderboard"]]
        ]
    },
    {
        "doctype": "Calendar View",
        "filters": [
            ["name", "in", ["AFL"]]
        ]
    },
    {
        "doctype": "Kanban Board",
        "filters": [
            ["name", "in", ["Все задачи"]]
        ]
    },
    {
        "doctype": "Issue Type",
        "filters": [
            ["name", "in", ["ЗНО", "ЗНИ", "Инцидент"]]
        ]
    },
    {
        "doctype": "Task Type",
        "filters": [
            ["name", "in", ["Issue", "Sprint", "Stage", "Phase"]]
        ]
    },
    {
        "doctype": "Custom Field",
        "filters": [
            ["module", "in", ["Dinext Projects"]]
        ]
    },
    {
        "doctype": "Property Setter",
        "filters": [
            ["module", "in", ["Dinext Projects"]]
        ]
    },
    {
        "doctype": "Client Script",
        "filters": [
            ["module", "in", ["Dinext Projects"]],
            ["enabled", "=", 1]
        ]
    },
    {
        "doctype": "Server Script",
        "filters": [
            ["module", "in", ["Dinext Projects"]],
            ["disabled", "=", 0]
        ]
    },
    {
        "doctype": "Web Page",
        "filters": [
            ["module", "in", ["Dinext Projects"]],       
        ]
    },
    {
        "doctype": "Role",
        "filters": [
            ["name", "like", "%Dinext%"],
            ["disabled", "=", 0]
        ]
    },
    {
        "doctype": "Custom DocPerm",
        "filters": [
            ["role", "like", "%Dinext%"]
        ]
    },
    {
        "doctype": "Working Hours On Date",
        "filters": [
            ["name", "in", "Сокращенные рабочие дни РФ"]
        ]
    },    
    {
        "doctype": "Timesheet Template",
        "filters": [
            ["name", "in", "Внутренняя команда РФ"]
        ]
    },    
    {
        "doctype": "Workflow",
        "filters": [
            ["document_type", "in", ["Application For Leave", "User Timesheet Position", "Project", "Expense Claim", "Purchase Invoice", "Sales Invoice"]],
            ["is_active", "=", 1]            
        ]
    },    
    {
        "doctype": "DocType Permission",
        "filters": [
            ["ref_doctype", "in", 
                [
                    "ToDo",
                    "Sales Invoice",
                    "Purchase Invoice",
                    "Timesheet Template",
                    "User Timesheet",
                    "User Timesheet Position",
                    "Worker",
                    "Task",
                    "Issue",
                    "User Delegate",
                    "Meeting Notes",
                    "GL Entry",
                    "Application For Leave"
                ]
            ],
            ["docstatus", "!=", 2]            
        ]
    }
]
''' '''


# Для выгрузки отчетов через fixtures - разблокировать строки ниже
#fixtures = [
#    {
#        "dt": "Report",
#        "filters": {"name": ("in", [
#                                    "Статус по всем ком.проектам",
#                                    "Мои задачи по датам",
#                                    "Контроль ставок по проектам",
#                                    "Отчет по утилизации",
#                                    "Контроль ставок по T&M проектам_V2",
#                                    "Контроль ставок по T&M проектам",
#                                    "Статистика по ТШ",
#                                    "Отчет по ТШ",
#                                    "Отчет для Подрядчиков"
#                                   ])
#                   },
#    },
#]
# ------------------

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "dinext_projects",
# 		"logo": "/assets/dinext_projects/logo.png",
# 		"title": "Dinext Projects",
# 		"route": "/dinext_projects",
# 		"has_permission": "dinext_projects.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/dinext_projects/css/dinext_projects.css"
# app_include_js = "/assets/dinext_projects/js/dinext-desk.js"

# include js, css files in header of web template
# web_include_css = "/assets/dinext_projects/css/dinext_projects.css"
# web_include_js = "/assets/dinext_projects/js/dinext_projects.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "dinext_projects/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# Work Efforts UI → project_workload_assignment (ISS-2026-00002)
# User Timesheet UI → public/js/user_timesheet (ISS-2026-00926 try3)
doctype_js = {
	"User Timesheet": "public/js/user_timesheet/entry.js",
	"User Timesheet Position": "public/js/user_timesheet_position/form/route.js",
}
doctype_list_js = {
	"User Timesheet": [
		# reprocess helpers before status_color onload
		"public/js/user_timesheet/list/reprocess_je.js",
		"public/js/user_timesheet/list/status_color.js",
	],
	"User Timesheet Position": [
		"public/js/user_timesheet_position/list/style.js",
		"public/js/user_timesheet_position/list/period_filter.js",
		"public/js/user_timesheet_position/list/functions.js",
		"public/js/user_timesheet_position/list/history.js",
		"public/js/user_timesheet_position/list/custom_listview.js",
	],
}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "dinext_projects/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "dinext_projects.utils.jinja_methods",
# 	"filters": "dinext_projects.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "dinext_projects.install.before_install"
after_install = "dinext_projects.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "dinext_projects.uninstall.before_uninstall"
# after_uninstall = "dinext_projects.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "dinext_projects.utils.before_app_install"
# after_app_install = "dinext_projects.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "dinext_projects.utils.before_app_uninstall"
# after_app_uninstall = "dinext_projects.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "dinext_projects.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events
# User Timesheet domain events (ISS-2026-00926 try3 phase 2 block A)
# Canon bodies: demodev Server Scripts — disable matching SS on site after cutover.

doc_events = {
	"User Timesheet": {
		"before_save": "dinext_projects.dinext_projects.user_timesheet.events.user_timesheet.before_save",
		# Server Script "After Save" ≡ Document.on_update (JE create/cancel)
		"on_update": "dinext_projects.dinext_projects.user_timesheet.events.user_timesheet.on_update",
	},
	"User Timesheet Position": {
		"before_insert": "dinext_projects.dinext_projects.user_timesheet.events.user_timesheet_position.before_insert",
		"before_save": "dinext_projects.dinext_projects.user_timesheet.events.user_timesheet_position.before_save",
		# Server Script "After Save" ≡ Document.on_update
		# Layer 3 ISS-2026-03288: UTP→UT rollup + Task act_* (SS UTP_UT_Status_V3 disabled local)
		"on_update": "dinext_projects.dinext_projects.user_timesheet.events.user_timesheet_position.on_update",
		"on_trash": "dinext_projects.dinext_projects.user_timesheet.events.user_timesheet_position.on_trash",
	},
	"Comment": {
		# Server Script "After Insert" ≡ Document.after_insert
		"after_insert": "dinext_projects.dinext_projects.user_timesheet.events.comment.transfer_utp_comment_to_ut",
	},
}

# Scheduled Tasks
# ---------------
# TSCrW2 weekly UT create (ISS-2026-00926 phase 2 F). Demodev cron: Mon 08:30.

scheduler_events = {
	"cron": {
		"30 8 * * 1": [
			"dinext_projects.dinext_projects.user_timesheet.scheduler.create_weekly_timesheets",
		],
	},
}

# Testing
# -------

# before_tests = "dinext_projects.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "dinext_projects.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "dinext_projects.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["dinext_projects.utils.before_request"]
# after_request = ["dinext_projects.utils.after_request"]

# Job Events
# ----------
# before_job = ["dinext_projects.utils.before_job"]
# after_job = ["dinext_projects.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"dinext_projects.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }
