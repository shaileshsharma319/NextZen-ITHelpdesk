"""
Bulk seed users with default password: Welcome@1234
Usage: python seed_users.py
"""
from app import create_app, db
from app.models.user import User
from datetime import date

app = create_app()

DEFAULT_PASSWORD = "Welcome@1234"

# (full_name, first_name, last_name)
USERS = [
    ("Sudesh Ingole",           "Sudesh",     "Ingole"),
    ("Ali Hasan Khan",          "Ali",        "Hasan Khan"),
    ("Om Patil",                "Om",         "Patil"),
    ("Secondary Domain",        "Secondary",  "Domain"),
    ("Suyog Zambare",           "Suyog",      "Zambare"),
    ("Jay Dalal",               "Jay",        "Dalal"),
    ("Akshay Shah",             "Akshay",     "Shah"),
    ("Ashutosh Dubey",          "Ashutosh",   "Dubey"),
    ("Rakesh Kumar Dash",       "Rakesh",     "Kumar Dash"),
    ("Pratik Jadhav",           "Pratik",     "Jadhav"),
    ("Yash Dhapodkar",          "Yash",       "Dhapodkar"),
    ("Nikhil Sarde",            "Nikhil",     "Sarde"),
    ("Raj Kumar",               "Raj",        "Kumar"),
    ("Shailesh Sharma",         "Shailesh",   "Sharma"),
    ("Shiv Shankar Pandit",     "Shiv",       "Shankar Pandit"),
    ("Ajay Sonawale",           "Ajay",       "Sonawale"),
    ("Soumitra Sir IIS VM",     "Soumitra",   "Sir IIS VM"),
    ("Shreyas Jadhav",          "Shreyas",    "Jadhav"),
    ("App Support",             "App",        "Support"),
    ("Pradeep Sawant",          "Pradeep",    "Sawant"),
    ("Rounak Ghosh",            "Rounak",     "Ghosh"),
    ("Sahili Choure",           "Sahili",     "Choure"),
    ("Pratham Jogi",            "Pratham",    "Jogi"),
    ("Shobhnath Yadav",         "Shobhnath",  "Yadav"),
    ("Siddharth Singh",         "Siddharth",  "Singh"),
    ("Mohit Patil",             "Mohit",      "Patil"),
    ("Amit Singh",              "Amit",       "Singh"),
    ("Hemangi Khot",            "Hemangi",    "Khot"),
    ("Ankur Kadam",             "Ankur",      "Kadam"),
    ("Onkar Mhaske",            "Onkar",      "Mhaske"),
    ("Riya Thakkar",            "Riya",       "Thakkar"),
    ("Rushikesh Patil",         "Rushikesh",  "Patil"),
    ("Soham Pathak",            "Soham",      "Pathak"),
    ("Sanket Mahadik",          "Sanket",     "Mahadik"),
    ("Aryan Garate",            "Aryan",      "Garate"),
    ("Laxmi Shinde",            "Laxmi",      "Shinde"),
    ("Pranita Pawar",           "Pranita",    "Pawar"),
    ("Pranay Kamble",           "Pranay",     "Kamble"),
    ("Anand Sharma",            "Anand",      "Sharma"),
    ("Vaishnavi Mhaske",        "Vaishnavi",  "Mhaske"),
    ("Shubham Ghule",           "Shubham",    "Ghule"),
    ("Narayan Kale",            "Narayan",    "Kale"),
    ("Prakash Choure",          "Prakash",    "Choure"),
    ("Sneha Sonawane",          "Sneha",      "Sonawane"),
    ("Shubham Kumawat",         "Shubham",    "Kumawat"),
    ("Saiteja Adepu",           "Saiteja",    "Adepu"),
    ("Sanket Mulay",            "Sanket",     "Mulay"),
    ("Teja Borapureddi",        "Teja",       "Borapureddi"),
    ("Tanish Thomabre",         "Tanish",     "Thomabre"),
    ("Supriya Malbari",         "Supriya",    "Malbari"),
    ("Sayali Bhandari",         "Sayali",     "Bhandari"),
    ("Sanvi Patil",             "Sanvi",      "Patil"),
    ("Ankita Angne",            "Ankita",     "Angne"),
    ("Ashish Gupta",            "Ashish",     "Gupta"),
    ("Rushang Thakkar",         "Rushang",    "Thakkar"),
    ("Shiv Shankar Pandit 2",   "Shiv",       "Shankar Pandit"),   # duplicate name → suffix
    ("Param Uni",               "Param",      "Uni"),
    ("Apeksha Patil",           "Apeksha",    "Patil"),
    ("Jay Phad",                "Jay",        "Phad"),
    ("Trupti Tilwe",            "Trupti",     "Tilwe"),
    ("Soumitra Chatterjee",     "Soumitra",   "Chatterjee"),
    ("Rajesh Jadhav",           "Rajesh",     "Jadhav"),
    ("Kishor Shirsath",         "Kishor",     "Shirsath"),
    ("Vandana Chinchavale",     "Vandana",    "Chinchavale"),
    ("Tulika Kanaujia",         "Tulika",     "Kanaujia"),
    ("Tanaya Kumbharkar",       "Tanaya",     "Kumbharkar"),
    ("Dhanashree Pednekar",     "Dhanashree", "Pednekar"),
    ("Srinivas Alwala",         "Srinivas",   "Alwala"),
    ("Poonam Hinge",            "Poonam",     "Hinge"),
    ("Govind Sir",              "Govind",     "Sir"),
]


def make_email(first, last, used_emails):
    """firstname.lastname@helpdesk.com, de-duplicated with numeric suffix"""
    base_first = first.split()[0].lower()
    base_last  = last.split()[0].lower()
    base = f"{base_first}.{base_last}@helpdesk.com"
    if base not in used_emails:
        return base
    i = 2
    while f"{base_first}.{base_last}{i}@helpdesk.com" in used_emails:
        i += 1
    return f"{base_first}.{base_last}{i}@helpdesk.com"


def make_username(first, last, used_usernames):
    base_first = first.split()[0].lower()
    base_last  = last.split()[0].lower()
    base = f"{base_first}.{base_last}"
    if base not in used_usernames:
        return base
    i = 2
    while f"{base_first}.{base_last}{i}" in used_usernames:
        i += 1
    return f"{base_first}.{base_last}{i}"


with app.app_context():
    used_emails    = {u.email for u in User.query.all()}
    used_usernames = {u.username for u in User.query.filter(User.username.isnot(None)).all()}
    used_emp_ids   = {u.employee_id for u in User.query.filter(User.employee_id.isnot(None)).all()}

    last_user = User.query.order_by(User.id.desc()).first()
    next_num  = (last_user.id + 1) if last_user else 1

    created = []
    skipped = []

    for full_name, first, last in USERS:
        email    = make_email(first, last, used_emails)
        username = make_username(first, last, used_usernames)

        emp_id = f"EMP{next_num:04d}"
        while emp_id in used_emp_ids:
            next_num += 1
            emp_id = f"EMP{next_num:04d}"

        user = User(
            employee_id = emp_id,
            first_name  = first,
            last_name   = last,
            name        = full_name,
            email       = email,
            username    = username,
            role        = 'user',
            date_of_joining = date.today(),
        )
        user.set_password(DEFAULT_PASSWORD)
        db.session.add(user)

        used_emails.add(email)
        used_usernames.add(username)
        used_emp_ids.add(emp_id)
        created.append((emp_id, full_name, email, username))
        next_num += 1

    db.session.commit()

    print(f"\n{'EmpID':<10} {'Full Name':<28} {'Email':<38} {'Username'}")
    print("-" * 100)
    for emp_id, name, email, username in created:
        print(f"{emp_id:<10} {name:<28} {email:<38} {username}")

    print(f"\n{len(created)} users created.")
    print(f"  Default password : {DEFAULT_PASSWORD}")
