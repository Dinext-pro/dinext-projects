"""Contribution to the shared Workflow cutover from this application."""


def configuration():
    return {'remove': {'Server Script': ('Workflow Task Assign',
                                  'AFL WT After Save',
                                  'AFL WT Before Save',
                                  'AFL_Deleted_WTs_Deleted'),
                'Client Script': ('AFL_Approval_V3', 'Множественное_Согласование_AFL_V3'),
                'Notification': ('Требуется согласование', 'Требуется исправление')},
     'retain': {'Server Script': ('AFL_Calculate_Hours', 'AFL_Projects')},
     'retained_client_scripts': ('ApFL_Status_Color',),
     'retained_server_scripts': ('AFL_Calculate_Hours', 'AFL_Projects'),
     'queue_doctypes': ('Application For Leave',),
     'fixture_files': (('dinext_projects', 'fixtures/server_script.json', 'Server Script'),
                       ('dinext_projects', 'fixtures/client_script.json', 'Client Script'),
                       ('dinext_projects', 'fixtures/custom_docperm.json', 'Custom DocPerm')),
     'notification_files': (('dinext_projects',
                             'dinext_projects/notification/требуется_согласование',
                             'Требуется согласование'),
                            ('dinext_projects',
                             'dinext_projects/notification/требуется_исправление',
                             'Требуется исправление')),
     "migrate_settings": (20, _migrate_settings)}



def _migrate_settings():
    from dinext_projects.application_for_leave import configure_application_for_leave

    configure_application_for_leave()
