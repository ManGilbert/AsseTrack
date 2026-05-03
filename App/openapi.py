from copy import deepcopy


def _json_content(schema_ref=None, example=None):
    content = {"application/json": {}}
    if schema_ref:
        content["application/json"]["schema"] = schema_ref
    if example is not None:
        content["application/json"]["example"] = example
    return content


def _response(description, schema_ref=None, example=None):
    return {
        "description": description,
        "content": _json_content(schema_ref=schema_ref, example=example),
    }


def _request_body(schema_ref=None, example=None, required=True):
    return {
        "required": required,
        "content": _json_content(schema_ref=schema_ref, example=example),
    }


def _bearer_security():
    return [{"bearerAuth": []}]


def build_openapi_schema():
    auth_success_example = {
        "message": "Login successful as head_office_manager.",
        "user": {
            "id": 1,
            "email": "claudine.mukamana@assetrack.rw",
            "role": "head_office_manager",
            "is_active": True,
            "created_at": "2026-04-28T17:28:04.104173Z",
            "employee": {
                "id": 1,
                "full_name": "Claudine Mukamana",
                "branch_id": None,
                "position": "Chief Operations Officer",
            },
        },
        "access": "<jwt-access-token>",
        "refresh": "<jwt-refresh-token>",
    }

    schema = {
        "openapi": "3.0.3",
        "info": {
            "title": "AsseTrack API",
            "version": "1.0.0",
            "description": (
                "Interactive API documentation for AsseTrack, a Django REST Framework asset "
                "tracking platform for head offices, branches, employees, devices, device "
                "assignments, and repair/issue requests.\n\n"
                "Authentication: send `Authorization: Bearer <access_token>` on protected endpoints.\n"
                "Use POST `/api/auth/login/` with `admin@admin.com` / `Aa@2026123` to generate an access token for protected operations.\n\n"
                "Role-based flows:\n"
                "1. Head Office Manager: create head offices, branches, employees, devices, approve final requests.\n"
                "2. Branch Manager: manage only their branch employees, devices, assignments, and branch approvals.\n"
                "3. Employee: view own profile, assigned devices, and create/view own requests."
            ),
        },
        "servers": [{"url": "/"}],
        "tags": [
            {"name": "Auth", "description": "Authentication and current-user endpoints."},
            {"name": "Head Offices", "description": "Head office management endpoints."},
            {"name": "Branches", "description": "Branch management and branch-scoped listings."},
            {"name": "Employees", "description": "Employee profile and staff management endpoints."},
            {"name": "Devices", "description": "Device inventory management endpoints."},
            {"name": "Assignments", "description": "Device assignment and return workflow."},
            {"name": "Requests", "description": "Repair and issue request workflow endpoints."},
        ],
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                }
            },
            "schemas": {
                "User": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "email": {"type": "string", "format": "email"},
                        "role": {"type": "string"},
                        "is_active": {"type": "boolean"},
                        "created_at": {"type": "string", "format": "date-time"},
                        "employee": {
                            "type": "object",
                            "nullable": True,
                            "properties": {
                                "id": {"type": "integer"},
                                "full_name": {"type": "string"},
                                "branch_id": {"type": "integer", "nullable": True},
                                "position": {"type": "string"},
                            },
                        },
                    },
                },
                "AuthPayload": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string"},
                        "user": {"$ref": "#/components/schemas/User"},
                        "access": {"type": "string"},
                        "refresh": {"type": "string"},
                    },
                },
                "RegisterRequest": {
                    "type": "object",
                    "required": [
                        "email",
                        "password",
                        "role",
                        "first_name",
                        "last_name",
                        "phone",
                        "position",
                        "department",
                        "hire_date",
                    ],
                    "properties": {
                        "email": {"type": "string", "format": "email"},
                        "password": {"type": "string", "format": "password"},
                        "role": {
                            "type": "string",
                            "enum": ["head_office_manager", "branch_manager", "employee"],
                        },
                        "first_name": {"type": "string"},
                        "last_name": {"type": "string"},
                        "phone": {"type": "string"},
                        "position": {"type": "string"},
                        "department": {"type": "string"},
                        "hire_date": {"type": "string", "format": "date"},
                        "branch": {"type": "integer", "nullable": True},
                    },
                },
                "LoginRequest": {
                    "type": "object",
                    "required": ["email", "password"],
                    "properties": {
                        "email": {"type": "string", "format": "email"},
                        "password": {"type": "string", "format": "password"},
                        "role": {
                            "type": "string",
                            "enum": ["head_office_manager", "branch_manager", "employee"],
                        },
                    },
                },
                "RefreshRequest": {
                    "type": "object",
                    "required": ["refresh"],
                    "properties": {"refresh": {"type": "string"}},
                },
                "HeadOffice": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                        "branch_count": {"type": "integer"},
                        "created_at": {"type": "string", "format": "date-time"},
                    },
                },
                "Branch": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                        "head_office": {"type": "integer"},
                        "manager": {"type": "integer", "nullable": True},
                        "created_at": {"type": "string", "format": "date-time"},
                    },
                },
                "EmployeeWrite": {
                    "type": "object",
                    "required": [
                        "user",
                        "branch",
                        "first_name",
                        "last_name",
                        "phone",
                        "position",
                        "department",
                        "hire_date",
                        "is_active",
                    ],
                    "properties": {
                        "user": {
                            "type": "object",
                            "required": ["email", "password", "role"],
                            "properties": {
                                "email": {"type": "string", "format": "email"},
                                "password": {"type": "string", "format": "password"},
                                "role": {
                                    "type": "string",
                                    "enum": ["head_office_manager", "branch_manager", "employee"],
                                },
                                "is_active": {"type": "boolean"},
                            },
                        },
                        "branch": {"type": "integer", "nullable": True},
                        "first_name": {"type": "string"},
                        "last_name": {"type": "string"},
                        "phone": {"type": "string"},
                        "position": {"type": "string"},
                        "department": {"type": "string"},
                        "hire_date": {"type": "string", "format": "date"},
                        "is_active": {"type": "boolean"},
                    },
                },
                "Employee": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "user": {"$ref": "#/components/schemas/User"},
                        "branch": {"type": "integer", "nullable": True},
                        "first_name": {"type": "string"},
                        "last_name": {"type": "string"},
                        "full_name": {"type": "string"},
                        "phone": {"type": "string"},
                        "position": {"type": "string"},
                        "department": {"type": "string"},
                        "hire_date": {"type": "string", "format": "date"},
                        "is_active": {"type": "boolean"},
                        "is_head_office": {"type": "boolean"},
                        "assigned_devices_count": {"type": "integer"},
                        "created_at": {"type": "string", "format": "date-time"},
                    },
                },
                "Device": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                        "device_type": {"type": "string"},
                        "branch": {"type": "integer", "nullable": True},
                        "serial_number": {"type": "string"},
                        "brand": {"type": "string"},
                        "model": {"type": "string"},
                        "purchase_date": {"type": "string", "format": "date", "nullable": True},
                        "assign_to_all_branches": {"type": "boolean"},
                        "assignment_scope": {"type": "string"},
                        "created_at": {"type": "string", "format": "date-time"},
                    },
                },
                "AssignDeviceRequest": {
                    "type": "object",
                    "required": ["device", "employee"],
                    "properties": {
                        "device": {"type": "integer"},
                        "employee": {"type": "integer"},
                    },
                },
                "Assignment": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "device": {"type": "integer"},
                        "employee": {"type": "integer"},
                        "branch": {"type": "integer", "nullable": True},
                        "assigned_at": {"type": "string", "format": "date-time"},
                        "returned_at": {"type": "string", "format": "date-time", "nullable": True},
                        "is_active": {"type": "boolean"},
                    },
                },
                "RequestCreate": {
                    "type": "object",
                    "required": ["device", "issue_description"],
                    "properties": {
                        "device": {"type": "integer"},
                        "issue_description": {"type": "string"},
                    },
                },
                "RequestDecision": {
                    "type": "object",
                    "properties": {
                        "reason": {"type": "string"},
                        "notes": {"type": "string"},
                    },
                },
                "RepairRequest": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "employee": {"type": "integer"},
                        "device": {"type": "integer"},
                        "issue_description": {"type": "string"},
                        "status": {
                            "type": "string",
                            "enum": [
                                "pending",
                                "approved_by_branch",
                                "approved_by_head_office",
                                "rejected",
                                "resolved",
                            ],
                        },
                        "rejection_reason": {"type": "string"},
                        "resolution_notes": {"type": "string"},
                        "approved_by_branch_at": {"type": "string", "format": "date-time", "nullable": True},
                        "approved_by_head_office_at": {"type": "string", "format": "date-time", "nullable": True},
                        "resolved_at": {"type": "string", "format": "date-time", "nullable": True},
                        "rejected_at": {"type": "string", "format": "date-time", "nullable": True},
                        "progress_percentage": {"type": "integer"},
                        "created_at": {"type": "string", "format": "date-time"},
                        "updated_at": {"type": "string", "format": "date-time"},
                    },
                },
            },
        },
        "paths": {},
    }

    paths = schema["paths"]

    paths["/api/auth/register/"] = {
        "post": {
            "tags": ["Auth"],
            "summary": "Register user",
            "description": "Public endpoint. Creates a user and matching employee profile.",
            "requestBody": _request_body(
                {"$ref": "#/components/schemas/RegisterRequest"},
                {
                    "email": "claudine.mukamana@assetrack.rw",
                    "password": "StrongPass123!",
                    "role": "head_office_manager",
                    "first_name": "Claudine",
                    "last_name": "Mukamana",
                    "phone": "+250788100001",
                    "position": "Chief Operations Officer",
                    "department": "Operations",
                    "hire_date": "2021-03-12",
                },
            ),
            "responses": {
                "201": _response("Registration successful.", {"$ref": "#/components/schemas/AuthPayload"}, auth_success_example),
                "400": _response("Validation error."),
            },
        }
    }

    paths["/api/auth/login/"] = {
        "post": {
            "tags": ["Auth"],
            "summary": "Login",
            "requestBody": _request_body(
                {"$ref": "#/components/schemas/LoginRequest"},
                {
                    "email": "claudine.mukamana@assetrack.rw",
                    "password": "StrongPass123!",
                    "role": "head_office_manager",
                },
            ),
            "responses": {
                "200": _response("Login successful.", {"$ref": "#/components/schemas/AuthPayload"}, auth_success_example),
                "400": _response("Invalid credentials or role."),
            },
        }
    }

    paths["/api/auth/logout/"] = {
        "post": {
            "tags": ["Auth"],
            "summary": "Logout",
            "security": _bearer_security(),
            "requestBody": _request_body(
                {"$ref": "#/components/schemas/RefreshRequest"},
                {"refresh": "<jwt-refresh-token>"},
            ),
            "responses": {
                "205": _response("Logout successful.", example={"message": "Logout successful."}),
                "400": _response("Invalid refresh token."),
            },
        }
    }

    paths["/api/auth/me/"] = {
        "get": {
            "tags": ["Auth"],
            "summary": "Current user",
            "security": _bearer_security(),
            "responses": {
                "200": _response("Current authenticated user.", {"$ref": "#/components/schemas/User"}),
                "401": _response("Unauthorized."),
            },
        }
    }

    paths["/api/auth/token/refresh/"] = {
        "post": {
            "tags": ["Auth"],
            "summary": "Refresh JWT token",
            "requestBody": _request_body(
                {"$ref": "#/components/schemas/RefreshRequest"},
                {"refresh": "<jwt-refresh-token>"},
            ),
            "responses": {
                "200": _response("New access token.", example={"access": "<new-access-token>"}),
                "401": _response("Invalid or expired refresh token."),
            },
        }
    }

    def crud_collection(path, tag, summary_prefix, schema_name, create_example=None, security=True, list_description=None):
        entry = {
            "get": {
                "tags": [tag],
                "summary": f"List {summary_prefix}",
                "responses": {
                    "200": _response("Paginated list.", example={"count": 10, "next": None, "previous": None, "results": []}),
                },
            },
            "post": {
                "tags": [tag],
                "summary": f"Create {summary_prefix[:-1] if summary_prefix.endswith('s') else summary_prefix}",
                "responses": {
                    "201": _response("Created successfully.", {"$ref": f"#/components/schemas/{schema_name}"}),
                    "400": _response("Validation error."),
                },
            },
        }
        if list_description:
            entry["get"]["description"] = list_description
        if create_example:
            entry["post"]["requestBody"] = _request_body({"$ref": f"#/components/schemas/{schema_name}"}, create_example)
        if security:
            entry["get"]["security"] = _bearer_security()
            entry["post"]["security"] = _bearer_security()
        return entry

    def crud_detail(path, tag, schema_name, security=True):
        entry = {
            "get": {
                "tags": [tag],
                "summary": f"Retrieve {schema_name}",
                "responses": {"200": _response("Object detail.", {"$ref": f"#/components/schemas/{schema_name}"})},
            },
            "put": {
                "tags": [tag],
                "summary": f"Update {schema_name}",
                "responses": {
                    "200": _response("Updated successfully.", {"$ref": f"#/components/schemas/{schema_name}"}),
                    "400": _response("Validation error."),
                },
            },
            "patch": {
                "tags": [tag],
                "summary": f"Partially update {schema_name}",
                "responses": {
                    "200": _response("Updated successfully.", {"$ref": f"#/components/schemas/{schema_name}"}),
                    "400": _response("Validation error."),
                },
            },
            "delete": {
                "tags": [tag],
                "summary": f"Delete {schema_name}",
                "responses": {"204": {"description": "Deleted successfully."}},
            },
        }
        if security:
            for method in entry.values():
                method["security"] = _bearer_security()
        return entry

    paths["/api/head-offices/"] = crud_collection(
        "/api/head-offices/",
        "Head Offices",
        "Head Offices",
        "HeadOffice",
        create_example={"name": "Kigali Central Head Office"},
    )
    paths["/api/head-offices/{id}/"] = crud_detail("/api/head-offices/{id}/", "Head Offices", "HeadOffice")
    paths["/api/head-offices/{id}/branches/"] = {
        "get": {
            "tags": ["Head Offices"],
            "summary": "List branches under head office",
            "security": _bearer_security(),
            "responses": {"200": _response("Branches under this head office.", example=[])},
        }
    }
    paths["/api/head-offices/{id}/devices/"] = {
        "get": {
            "tags": ["Head Offices"],
            "summary": "List devices under head office",
            "security": _bearer_security(),
            "responses": {"200": _response("Devices under this head office.", example=[])},
        }
    }

    paths["/api/branches/"] = {
        "get": {
            "tags": ["Branches"],
            "summary": "List branches",
            "security": _bearer_security(),
            "responses": {"200": _response("Paginated branches.", example={"count": 10, "results": []})},
        },
        "post": {
            "tags": ["Branches"],
            "summary": "Create branch",
            "security": _bearer_security(),
            "requestBody": _request_body(
                {"$ref": "#/components/schemas/Branch"},
                {"name": "Kigali Branch", "head_office": 1},
            ),
            "responses": {
                "201": _response("Branch created.", {"$ref": "#/components/schemas/Branch"}),
                "403": _response("Only head office managers can create branches."),
            },
        },
    }
    paths["/api/branches/{id}/"] = crud_detail("/api/branches/{id}/", "Branches", "Branch")
    paths["/api/branches/{id}/assign_manager/"] = {
        "post": {
            "tags": ["Branches"],
            "summary": "Assign branch manager",
            "security": _bearer_security(),
            "requestBody": _request_body(None, {"manager": 3}),
            "responses": {
                "200": _response("Manager assigned.", {"$ref": "#/components/schemas/Branch"}),
                "400": _response("Invalid manager selection."),
            },
        }
    }
    paths["/api/branches/{id}/employees/"] = {
        "get": {
            "tags": ["Branches"],
            "summary": "List branch employees",
            "security": _bearer_security(),
            "responses": {"200": _response("Employees in branch.", example=[])},
        }
    }
    paths["/api/branches/{id}/devices/"] = {
        "get": {
            "tags": ["Branches"],
            "summary": "List branch devices",
            "security": _bearer_security(),
            "responses": {"200": _response("Devices in branch.", example=[])},
        }
    }

    paths["/api/employees/"] = {
        "get": {
            "tags": ["Employees"],
            "summary": "List employees",
            "security": _bearer_security(),
            "responses": {"200": _response("Paginated employees.", example={"count": 10, "results": []})},
        },
        "post": {
            "tags": ["Employees"],
            "summary": "Create employee",
            "security": _bearer_security(),
            "requestBody": _request_body(
                {"$ref": "#/components/schemas/EmployeeWrite"},
                {
                    "user": {
                        "email": "aline.niyigena@assetrack.rw",
                        "password": "StrongPass123!",
                        "role": "employee",
                    },
                    "branch": 1,
                    "first_name": "Aline",
                    "last_name": "Niyigena",
                    "phone": "+250788200001",
                    "position": "Finance Officer",
                    "department": "Finance",
                    "hire_date": "2022-01-10",
                    "is_active": True,
                },
            ),
            "responses": {
                "201": _response("Employee created.", {"$ref": "#/components/schemas/Employee"}),
                "403": _response("Role scope denied."),
            },
        },
    }
    paths["/api/employees/{id}/"] = crud_detail("/api/employees/{id}/", "Employees", "Employee")
    paths["/api/employees/profile/"] = {
        "get": {
            "tags": ["Employees"],
            "summary": "Get own employee profile",
            "security": _bearer_security(),
            "responses": {"200": _response("Current employee profile.", {"$ref": "#/components/schemas/Employee"})},
        }
    }
    paths["/api/employees/{id}/devices/"] = {
        "get": {
            "tags": ["Employees"],
            "summary": "List employee device assignments",
            "security": _bearer_security(),
            "responses": {"200": _response("Assignments for employee.", example=[])},
        }
    }

    paths["/api/devices/"] = {
        "get": {
            "tags": ["Devices"],
            "summary": "List devices",
            "description": "Supports filters: `branch`, `device_type`.",
            "security": _bearer_security(),
            "parameters": [
                {"name": "branch", "in": "query", "schema": {"type": "integer"}},
                {"name": "device_type", "in": "query", "schema": {"type": "string"}},
            ],
            "responses": {"200": _response("Paginated devices.", example={"count": 10, "results": []})},
        },
        "post": {
            "tags": ["Devices"],
            "summary": "Create device",
            "security": _bearer_security(),
            "requestBody": _request_body(
                {"$ref": "#/components/schemas/Device"},
                {
                    "name": "Dell Latitude 5440",
                    "device_type": "laptop",
                    "branch": 1,
                    "serial_number": "RW-KGL-LT-001",
                    "brand": "Dell",
                    "model": "Latitude 5440",
                    "purchase_date": "2025-02-15",
                    "assign_to_all_branches": False,
                },
            ),
            "responses": {
                "201": _response("Device created.", {"$ref": "#/components/schemas/Device"}),
                "403": _response("Employees cannot create devices."),
            },
        },
    }
    paths["/api/devices/{id}/"] = crud_detail("/api/devices/{id}/", "Devices", "Device")

    paths["/api/assignments/"] = {
        "get": {
            "tags": ["Assignments"],
            "summary": "List assignments",
            "security": _bearer_security(),
            "responses": {"200": _response("Paginated assignments.", example={"count": 10, "results": []})},
        },
        "post": {
            "tags": ["Assignments"],
            "summary": "Assign device to employee",
            "security": _bearer_security(),
            "requestBody": _request_body(
                {"$ref": "#/components/schemas/AssignDeviceRequest"},
                {"device": 1, "employee": 4},
            ),
            "responses": {
                "201": _response("Assignment created.", {"$ref": "#/components/schemas/Assignment"}),
                "400": _response("Device already assigned or invalid target."),
            },
        },
    }
    paths["/api/assignments/{id}/"] = {
        "get": {
            "tags": ["Assignments"],
            "summary": "Retrieve assignment",
            "security": _bearer_security(),
            "responses": {"200": _response("Assignment detail.", {"$ref": "#/components/schemas/Assignment"})},
        }
    }
    paths["/api/assignments/{id}/return_device/"] = {
        "post": {
            "tags": ["Assignments"],
            "summary": "Return assigned device",
            "security": _bearer_security(),
            "responses": {
                "200": _response("Device returned.", {"$ref": "#/components/schemas/Assignment"}),
                "400": _response("Assignment already closed."),
            },
        }
    }

    paths["/api/requests/"] = {
        "get": {
            "tags": ["Requests"],
            "summary": "List requests",
            "security": _bearer_security(),
            "responses": {"200": _response("Paginated requests.", example={"count": 10, "results": []})},
        },
        "post": {
            "tags": ["Requests"],
            "summary": "Create issue/repair request",
            "security": _bearer_security(),
            "requestBody": _request_body(
                {"$ref": "#/components/schemas/RequestCreate"},
                {"device": 1, "issue_description": "Battery drains too quickly during field work."},
            ),
            "responses": {
                "201": _response("Request created.", {"$ref": "#/components/schemas/RepairRequest"}),
                "403": _response("Only employees can create requests."),
            },
        },
    }
    paths["/api/requests/{id}/"] = {
        "get": {
            "tags": ["Requests"],
            "summary": "Retrieve request",
            "security": _bearer_security(),
            "responses": {"200": _response("Request detail.", {"$ref": "#/components/schemas/RepairRequest"})},
        }
    }
    paths["/api/requests/{id}/approve_branch/"] = {
        "post": {
            "tags": ["Requests"],
            "summary": "Branch-level approval",
            "description": "Branch manager only.",
            "security": _bearer_security(),
            "responses": {
                "200": _response("Request approved by branch.", {"$ref": "#/components/schemas/RepairRequest"}),
                "400": _response("Only pending requests can be branch-approved."),
            },
        }
    }
    paths["/api/requests/{id}/approve_head_office/"] = {
        "post": {
            "tags": ["Requests"],
            "summary": "Head office final approval",
            "description": "Head office manager only.",
            "security": _bearer_security(),
            "responses": {
                "200": _response("Request approved by head office.", {"$ref": "#/components/schemas/RepairRequest"}),
                "400": _response("Request must first be approved by branch."),
            },
        }
    }
    paths["/api/requests/{id}/reject/"] = {
        "post": {
            "tags": ["Requests"],
            "summary": "Reject request",
            "security": _bearer_security(),
            "requestBody": _request_body(
                {"$ref": "#/components/schemas/RequestDecision"},
                {"reason": "Warranty coverage expired and replacement was approved instead."},
            ),
            "responses": {
                "200": _response("Request rejected.", {"$ref": "#/components/schemas/RepairRequest"}),
                "400": _response("Request is already closed."),
            },
        }
    }
    paths["/api/requests/{id}/resolve/"] = {
        "post": {
            "tags": ["Requests"],
            "summary": "Resolve request",
            "security": _bearer_security(),
            "requestBody": _request_body(
                {"$ref": "#/components/schemas/RequestDecision"},
                {"notes": "Device repaired by Kigali service center and returned to employee."},
            ),
            "responses": {
                "200": _response("Request resolved.", {"$ref": "#/components/schemas/RepairRequest"}),
                "400": _response("Only head-office-approved requests can be resolved."),
            },
        }
    }
    paths["/api/requests/{id}/progress/"] = {
        "get": {
            "tags": ["Requests"],
            "summary": "Get request progress",
            "security": _bearer_security(),
            "responses": {
                "200": _response(
                    "Request progress.",
                    example={"request_id": 1, "status": "approved_by_head_office", "progress_percentage": 70},
                )
            },
        }
    }

    return schema
