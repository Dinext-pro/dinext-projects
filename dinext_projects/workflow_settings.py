"""Workflow defaults for the documents owned by this application."""


def email_profiles():
	return {
		"Project": {"workflow": "Project Approval", "approval_states": ('На согласовании',)},
	}
