"""Field-name alias tables for universal normalization (Module 10).

Keys are lowercased alias -> canonical universal field name. Parser packs may
extend this per-pack.
"""
from __future__ import annotations

FIELD_ALIASES: dict[str, str] = {
    # timestamps
    "timestamp": "timestamp", "time": "timestamp", "ts": "timestamp", "date": "timestamp",
    "datetime": "timestamp", "@timestamp": "timestamp", "eventtime": "timestamp",
    "event_time": "timestamp", "logtime": "timestamp",
    # host / device
    "host": "host", "hostname": "host", "device": "host", "devname": "host",
    "machine": "host", "server": "host", "dvc": "host", "computer": "host",
    "source_host": "host", "computername": "host", "workstation": "host", "workstationname": "host",
    # source name
    "source": "source", "log_source": "source", "sourcetype": "source",
    # identity
    "user": "username", "username": "username", "user_name": "username", "account": "username",
    "uid": "username", "userid": "username", "user_id": "username", "login": "username",
    "usr": "username", "accountname": "username", "samaccountname": "username",
    "targetusername": "username", "subjectusername": "username", "target_user": "username",
    "email": "email", "mail": "email", "email_address": "email", "user_email": "email",
    "emailaddress": "email",
    # network - source
    "src_ip": "source_ip", "srcip": "source_ip", "source_ip": "source_ip",
    "sourceip": "source_ip", "source_address": "source_ip", "client_ip": "source_ip",
    "clientip": "source_ip", "remote_ip": "source_ip", "remote_addr": "source_ip",
    "remoteip": "source_ip", "src": "source_ip", "ip": "source_ip", "ipaddress": "source_ip",
    "sourceaddress": "source_ip", "c_ip": "source_ip", "cip": "source_ip",
    "sourcenetworkaddress": "source_ip", "callingstationid": "source_ip",
    # network - destination
    "dst_ip": "destination_ip", "dstip": "destination_ip", "destination_ip": "destination_ip",
    "destip": "destination_ip", "dest_ip": "destination_ip", "dest_addr": "destination_ip",
    "dst": "destination_ip", "server_ip": "destination_ip", "target_ip": "destination_ip",
    "destinationaddress": "destination_ip", "s_ip": "destination_ip",
    # ports
    "src_port": "source_port", "srcport": "source_port", "source_port": "source_port",
    "sport": "source_port", "spt": "source_port", "client_port": "source_port",
    "dst_port": "destination_port", "dstport": "destination_port",
    "destination_port": "destination_port", "dport": "destination_port",
    "dpt": "destination_port", "server_port": "destination_port", "port": "destination_port",
    "ipport": "source_port",
    # protocol
    "protocol": "protocol", "proto": "protocol", "ip_proto": "protocol", "transport": "protocol",
    # classification
    "event": "event_type", "event_type": "event_type", "eventtype": "event_type",
    "event_name": "event_type", "eventname": "event_type", "type": "event_type",
    "category": "event_type", "activity": "event_type",
    "action": "action", "act": "action", "operation": "action", "verb": "action",
    "status": "status", "result": "status", "outcome": "status", "disposition": "status",
    "severity": "severity", "level": "severity", "lvl": "severity", "loglevel": "severity",
    "priority": "severity", "log_level": "severity",
    # process / service
    "process": "process", "proc": "process", "program": "process", "cmd": "process",
    "application": "service", "app": "service", "service": "service", "svc": "service",
    "logger": "process", "module": "process", "component": "process", "facility": "service",
    # http
    "url": "url", "uri": "url", "path": "url", "request_uri": "url", "requesturl": "url",
    "request": "url", "cs_uri_stem": "url",
    "http_method": "http_method", "method": "http_method", "verb_http": "http_method",
    "cs_method": "http_method", "request_method": "http_method",
    "response_code": "response_code", "status_code": "response_code",
    "statuscode": "response_code", "http_status": "response_code", "sc_status": "response_code",
    "resp_code": "response_code",
    # message
    "message": "message", "msg": "message", "text": "message", "description": "message",
    "detail": "message", "log": "message", "raw_message": "message", "body": "message",
}

# canonical fields that are integers
INT_FIELDS = {"source_port", "destination_port", "response_code"}

SEVERITY_ALIASES = {
    "0": "critical", "1": "critical", "2": "critical", "3": "high", "4": "medium",
    "5": "low", "6": "info", "7": "info",
    "emerg": "critical", "emergency": "critical", "panic": "critical",
    "alert": "critical", "crit": "critical", "critical": "critical", "fatal": "critical",
    "err": "high", "error": "high", "severe": "high",
    "warn": "medium", "warning": "medium",
    "notice": "low",
    "info": "info", "informational": "info", "information": "info",
    "debug": "info", "trace": "info", "verbose": "info", "fine": "info",
}
