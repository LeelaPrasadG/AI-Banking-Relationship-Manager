import json
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

USERS_FILE = 'users.json'

def init_users():
    """Initialize default users with hashed passwords"""
    users = {
        'loanagent': {
            'password': generate_password_hash('pwd123'),
            'roles': ['auto-loan'],
            'created_at': datetime.now().isoformat()
        },
        'cardagent': {
            'password': generate_password_hash('pwd123'),
            'roles': ['credit-card'],
            'created_at': datetime.now().isoformat()
        },
        'bankagent': {
            'password': generate_password_hash('pwd123'),
            'roles': ['banking'],
            'created_at': datetime.now().isoformat()
        },
        'cardbankagent': {
            'password': generate_password_hash('pwd123'),
            'roles': ['credit-card', 'banking'],
            'created_at': datetime.now().isoformat()
        }
    }
    
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w') as f:
            json.dump(users, f, indent=2)
        print(f"✓ Users initialized in {USERS_FILE}")
    
    return users

def load_users():
    """Load users from JSON file"""
    if not os.path.exists(USERS_FILE):
        return init_users()
    
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def authenticate_user(username, password):
    """Authenticate user with username and password"""
    users = load_users()
    
    if username not in users:
        return None, "Invalid username"
    
    user = users[username]
    if check_password_hash(user['password'], password):
        return {
            'username': username,
            'roles': user['roles']
        }, "Success"
    
    return None, "Invalid password"

def get_user_roles(username):
    """Get roles for a specific user"""
    users = load_users()
    if username in users:
        return users[username]['roles']
    return []

def user_has_role(username, role):
    """Check if user has access to a specific role"""
    roles = get_user_roles(username)
    return role in roles
