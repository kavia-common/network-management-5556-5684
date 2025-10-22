"""
Device schema reference (JSON Schema-like).

Fields:
- _id: string (MongoDB ObjectId as string)
- name: string (required)
- ip_address: string (required, IPv4)
- type: string (required, enum: router, switch, server)
- location: string (required)
- status: string (required, enum: online, offline, unknown)
- last_checked: string (date-time, optional)
- created_at: string (date-time, auto)
- updated_at: string (date-time, auto)
"""
